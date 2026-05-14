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
  {"date": "2024-01-02", "open": 10.5, "high": 10.8, "low": 10.3, "close": 10.6, "volume": 12345678, "amount": 1.3e8, "factor_qfq": 1.0, "factor_hfq": 1.5}
]
```

## 数据库

TimescaleDB hypertable：

```sql
CREATE TABLE kline_data (
    symbol        TEXT    NOT NULL,
    date          DATE    NOT NULL,
    open          NUMERIC(10,3),
    high          NUMERIC(10,3),
    low           NUMERIC(10,3),
    close         NUMERIC(10,3),
    volume        BIGINT,
    amount        NUMERIC(15,2),
    factor_qfq    NUMERIC(10,6),
    factor_hfq    NUMERIC(10,6),
    source        TEXT    NOT NULL,
    updated_at    TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (symbol, date)
);

SELECT create_hypertable('kline_data', 'date');
```

## 数据流

1. 解析请求参数（symbol, start, end, adjust）
2. 查询 DB 获取缓存记录
3. 比对请求范围与缓存记录，找出缺失日期区间
4. 对每个缺失区间按源优先级顺序尝试拉取，成功后写入 DB
5. 合并缓存数据与新增数据
6. 若 adjust 参数存在，对每条记录的 open/high/low/close 应用复权计算（原始价格 × 对应因子，factor_qfq 或 factor_hfq）
7. 返回 records 数组

## 缓存策略

| 数据范围 | 行为 | TTL |
|---------|------|-----|
| 当日 | 超 TTL 重新拉取覆盖 | 60s |
| 近 5 交易日 | 超 TTL 重新拉取覆盖 | 5min |
| 历史 (>5天) | 永不过期 | 永久 |

## 多源故障转移

统一接口 `fetch_kline(symbol, start, end) -> DataFrame`。对每个缺失区间按优先级尝试：sina 成功则停止；失败切 tencent；再失败切 eastmoney；全部失败则跳过该区间。

## 错误处理

| 场景 | 表现 | 状态码 |
|------|------|--------|
| 全部缓存命中 | 正常返回 | 200 |
| 部分缺失、源全部失败 | 返回已有数据，缺失跳过 | 200 |
| 全部缺失、源全部失败 | 空数组 | 200 |
| symbol 格式错误 | 错误信息 | 422 |
| DB 连接失败 | 服务不可用 | 503 |
| 源不可用+无缓存 | 空数组，降级不报错 | 200 |

## 项目结构

```
candlex/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models/
│   │   ├── kline.py
│   │   └── schemas.py
│   ├── router.py
│   ├── service.py
│   └── sources/
│       ├── base.py
│       ├── sina.py
│       ├── tencent.py
│       └── eastmoney.py
├── scripts/
│   └── init_db.sql
├── pyproject.toml
└── Dockerfile
```
