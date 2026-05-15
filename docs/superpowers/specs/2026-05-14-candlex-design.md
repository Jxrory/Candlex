# CandleX: 日K线查询缓存服务

## 概述

基于 FastAPI + TimescaleDB 的日K线查询服务，通过多数据源故障转移和行级缓存策略，解决 akshare 访问次数限制问题，为 AI 量化工具提供稳定可靠的 K 线数据。

## 数据源

统一代码格式 `{市场}.{代码}`：

| 统一代码 | 新浪 | 腾讯 | 东方财富 |
|---------|------|------|---------|
| SH.600519 | sh600519 | SH600519 | 600519 |
| SZ.000001 | sz000001 | SZ000001 | 000001 |
| BJ.830123 | bj830123 | BJ830123 | 830123 |

源优先级（故障转移）：sina → tencent → eastmoney

## 数据库

TimescaleDB hypertable：

### kline_data — 原始K线数据（只存原始价，不含复权因子）

```sql
CREATE TABLE kline_data (
    symbol      TEXT    NOT NULL,
    date        DATE    NOT NULL,
    open        NUMERIC(10,3),
    high        NUMERIC(10,3),
    low         NUMERIC(10,3),
    close       NUMERIC(10,3),
    volume      BIGINT,
    amount      NUMERIC(15,2),
    source      TEXT    NOT NULL,
    PRIMARY KEY (symbol, date)
);

SELECT create_hypertable('kline_data', 'date');
```

### corporate_events — 除权除息事件表（增量写入，永不更新）

```sql
CREATE TABLE corporate_events (
    symbol            TEXT    NOT NULL,
    ex_date           DATE    NOT NULL,
    cash_dividend     NUMERIC(10,6),       -- 每股现金股利(元)
    stock_dividend    NUMERIC(10,6),       -- 每股送股比例
    capitalization    NUMERIC(10,6),       -- 每股转增比例
    rights_ratio      NUMERIC(10,6),       -- 每股配股比例
    rights_price      NUMERIC(10,4),       -- 每股配股价(元)
    event_type        TEXT    NOT NULL,     -- 'dividend' | 'rights' | 'combined'
    source            TEXT    NOT NULL,
    PRIMARY KEY (symbol, ex_date, event_type)
);

SELECT create_hypertable('corporate_events', 'ex_date');
```

### trade_calendar

```sql
CREATE TABLE trade_calendar (
    trade_date  DATE  PRIMARY KEY,
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

SELECT create_hypertable('trade_calendar', 'trade_date', if_not_exists => TRUE);
```

## 事件驱动复权

### 原理

不复权因子做全量快照，而是存储原始除权除息事件，查询时按需计算因子。

单个事件调整系数（理论除权公式）：

```
adj = (prev_close + rights_price × Rr - D) / (prev_close × (1 + Rs + Rc + Rr))
```

- C = ex_date 前一个交易日的收盘价
- D = 每股现金股利
- Rs = 每股送股比例
- Rc = 每股转增比例
- Rr = 每股配股比例
- Pr = 每股配股价

按日期累积：

| 因子 | 公式 |
|------|------|
| qfq_factor(d) | Π adjᵢ, 所有 ex_dateᵢ > d 的事件系数连乘 |
| hfq_factor(d) | 1 / Π adjᵢ, 所有 ex_dateᵢ ≤ d 的事件系数倒数连乘 |

### 复权算法

```python
def compute_factors(kline_date: date, events: list[CorporateEvent]) -> tuple[float, float]:
    qfq = 1.0
    hfq = 1.0
    for e in events:
        adj = e.adjustment_ratio   # 预先计算并缓存
        if e.ex_date > kline_date:
            qfq *= adj
        else:
            hfq /= adj  # 等价于乘以 1/adj
    return qfq, hfq
```

events 按 ex_date 升序排列，一次 O(N) 遍历即可对所有日期计算（N 通常 < 100）。

## API

### `GET /kline/{symbol}`

参数：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| start | date | 否 | 起始日期，默认一年前 |
| end | date | 否 | 截止日期，默认当天 |
| adjust | str | 否 | `qfq` / `hfq`，不传则返回原始价 |

返回：

```json
[
  {"date": "2024-01-02", "open": 10.5, "high": 10.8, "low": 10.3, "close": 10.6, "volume": 12345678, "amount": 1.3e8}
]
```

不返回 factor 字段（复权因子由客户端按需通过 /dividend 接口获取）。

### `GET /dividend/{symbol}`

参数：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| symbol | str | 是 | SH/SZ/BJ 格式股票代码 |
| start | date | 否 | 起始日期，默认不限制 |
| end | date | 否 | 截止日期，默认不限制 |

返回：

```json
[
  {
    "ex_date": "2023-08-25",
    "cash_dividend": 0.68,
    "stock_dividend": 0.0,
    "capitalization": 0.0,
    "rights_ratio": 0.0,
    "rights_price": null,
    "event_type": "dividend"
  }
]
```

### `GET /calendar`

参数：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| start | date | 否 | 起始日期，默认今年初 |
| end | date | 否 | 截止日期，默认今年末 |

返回：

```json
["2026-01-05", "2026-01-06", "2026-01-07"]
```

## 数据流

### K线查询

```
GET /kline → 查 kline_data（原始价） → 从 corporate_events 加载该 symbol 全部事件
  → 若需复权，对每条记录计算因子 → 复权 → 返回
```

### 事件获取（定时任务）

```
APScheduler 定时任务（每日开盘前）
  → 遍历待检查 symbol
  → 查 corporate_events 获取该 symbol 最大 ex_date
  → 若无记录或最大 ex_date < 当前季度末 → 从 akshare 拉取全量
  → INSERT ON CONFLICT DO NOTHING 写入 corporate_events
```

### K线获取（on-demand）

```
GET /kline → 查 kline_data 缓存
  → 缺失 / 过期 → 从 akshare 获取原始价（无需 factor 参数）
  → INSERT ON CONFLICT DO UPDATE 写入 kline_data
  → 从 corporate_events 加载事件 → 复权 → 返回
```

## 缓存策略

| 数据范围 | 行为 | TTL |
|---------|------|-----|
| 当日 | 超 TTL 重新拉取覆盖 | 60s |
| 近 5 交易日 | 超 TTL 重新拉取覆盖 | 5min |
| 历史 (>5天) | 永不过期 | 永久 |

## 定时任务

使用 APScheduler，FastAPI 启动时注册：

| 任务 | 调度 | 行为 |
|------|------|------|
| 同步分红配股 | 每日 08:30（开盘前） | 遍历活跃 symbol，增量拉取 corporate_events |
| 同步交易日历 | 每日 08:30 | 同现有逻辑 |

首次启动时全量拉取所有已缓存 symbol 的事件数据。

## DividendSource

新增数据源（独立于 K线 failover 链）：

```python
class DividendSource(BaseSource):
    """从新浪财经拉取分红配股事件"""

    async def fetch(self, symbol: str, start_date, end_date) -> pd.DataFrame:
        # 分红数据
        div = ak.stock_history_dividend_detail(sina_symbol, "分红", "")
        # 配股数据
        rights = ak.stock_history_dividend_detail(sina_symbol, "配股", "")
        # 合并、归一化到每股、过滤进度=实施
        return normalized_dataframe
```

symbol 转换规则：`SH.600519` → `600519`（去掉市场前缀）。
仅新浪数据源可用（腾讯/东财无等价接口）。

## 错误处理

| 场景 | 表现 | 状态码 |
|------|------|--------|
| 全部缓存命中 | 正常返回 | 200 |
| 部分缺失、源全部失败 | 返回已有数据，缺失跳过 | 200 |
| 全部缺失、源全部失败 | 空数组 | 200 |
| symbol 格式错误 | 错误信息 | 422 |
| DB 连接失败 | 服务不可用 | 503 |
| 分红配股源不可用 | 返回空数组 | 200 |

## 项目结构

```
candlex/
├── app/
│   ├── main.py             # + APScheduler 初始化
│   ├── config.py           # + dividend_sync_interval, dividend_sync_time
│   ├── database.py
│   ├── schemas.py          # + DividendRecord, -factor字段
│   ├── router.py           # + /dividend 路由
│   ├── service.py          # + 事件驱动复权计算，-factor UPSERT
│   ├── dividend.py         # 新增: DividendService（类似 CalendarService）
│   ├── calendar.py
│   └── sources/
│       ├── base.py
│       ├── sina.py          # -factor_qfq/factor_hfq 拉取
│       ├── tencent.py       # -factor_qfq/factor_hfq 拉取
│       ├── eastmoney.py     # -factor_qfq/factor_hfq 拉取
│       └── dividend.py      # 新增: DividendSource
├── scripts/
│   └── init_db.sql          # -factor列, +corporate_events 表
├── tests/
│   ├── conftest.py
│   ├── test_service.py
│   ├── test_router.py
│   ├── test_calendar.py
│   └── test_dividend.py     # 新增
├── pyproject.toml           # +apscheduler 依赖
└── Dockerfile
```

## 注意事项

- akshare 分红接口的分红/送转/配股字段是"每10股"单位，需要除以10归一化到"每股"
- stock_dividend 和 capitalization 都产生股本稀释，计算公式中合并处理
- adj 系数保留6位小数，与原来 NUMERIC(10,6) 精度一致
- 理论除权价与实际开盘价可能有偏差，但复权因子使用理论值（与交易所官方一致）
