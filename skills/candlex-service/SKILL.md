---
name: candlex-service
description: 使用场景：需要获取中国A股市场数据时——包括K线OHLCV、交易日历、分红/公司事件、基本面数据（v2，合并6张财务表）、选股筛选（v2，ROE/负债率/EPS等指标组合筛选）、个股新闻。基于akshare多源故障转移的缓存优先只读API。
---

# CandleX — 中国A股数据服务

缓存优先的只读API，提供中国A股市场数据。数据存储在TimescaleDB中，缓存未命中时自动从akshare（新浪/腾讯/东方财富）刷新。

核心约束：
- 所有数据均为只读
- 通过 `refresh=true` 参数主动触发刷新，或在缓存未命中时自动触发
- 请求不会阻塞等待上游——缓存优先，异步故障转移
- 股票代码格式必须匹配 `^(SH|SZ|BJ)\.[0-9]{6}$`

## API端点

所有端点返回JSON。基础URL默认为 `http://localhost:8000`。

### K线（OHLCV）

`GET /kline/{symbol}`

日K线数据，支持复权调整。

| 参数 | 类型 | 默认值 | 说明 |
|-------|------|--------|------|
| `start` | `YYYY-MM-DD` | 1年前 | 开始日期 |
| `end` | `YYYY-MM-DD` | 今天 | 结束日期 |
| `adjust` | `"qfq"` 或 `"hfq"` | 无 | 前复权或后复权 |

返回格式：
```json
[
  {
    "date": "2026-01-05",
    "open": 15.32,
    "high": 15.68,
    "low": 15.18,
    "close": 15.55,
    "volume": 12567800,
    "amount": 1.956e8
  }
]
```

### K线 + 技术指标

`GET /indicators/{symbol}`

日K线 + 实时计算的技术指标，支持复权和动态指定指标组合。

| 参数 | 类型 | 默认值 | 说明 |
|-------|------|--------|------|
| `start` | `YYYY-MM-DD` | 1年前 | 开始日期 |
| `end` | `YYYY-MM-DD` | 今天 | 结束日期 |
| `adjust` | `"qfq"` 或 `"hfq"` | 无 | 前复权或后复权，作用于K线数据 |
| `i` | 可重复 | 无 | 指标规格，详见下表 |

`i` 参数支持两种格式：
- 简写：`i=ma:5&i=ma:10&i=macd&i=rsi:14`
- JSON：`i=[{"name":"ma","params":{"n":5}}]`

支持 7 种指标及其默认参数：

| 名称 | 默认参数 | 简写示例 | 输出字段 |
|------|---------|----------|---------|
| `ma` | `n=20` | `ma:5` | `ma{n}` |
| `ema` | `n=20` | `ema:12` | `ema{n}` |
| `macd` | `fast=12,slow=26,signal=9` | `macd` | `macd_dif`, `macd_dea`, `macd_hist` |
| `rsi` | `n=14` | `rsi:14` | `rsi{n}` |
| `boll` | `n=20,k=2` | `boll:20,2` | `boll_mid`, `boll_upper`, `boll_lower` |
| `atr` | `n=14` | `atr:14` | `atr{n}` |
| `kdj` | `n=9,m1=3,m2=3` | `kdj:9,3,3` | `kdj_k`, `kdj_d`, `kdj_j` |

返回原始K线字段（date/open/high/low/close/volume/amount）+ 请求的指标列：

```json
[
  {
    "date": "2026-01-05",
    "open": 15.32,
    "high": 15.68,
    "low": 15.18,
    "close": 15.55,
    "volume": 12567800,
    "amount": 1.956e8,
    "ma5": 15.42,
    "ma10": 15.28,
    "macd_dif": 0.15,
    "macd_dea": 0.12,
    "macd_hist": 0.03
  }
]
```

指标值在服务端使用 pandas/numpy 实时计算，不缓存。NaN 序列化为 `null`。

### 分红与公司事件

`GET /dividend/{symbol}`

分红、送股、配股、转增等公司事件。

| 参数 | 类型 | 默认值 | 说明 |
|-------|------|--------|------|
| `start` | `YYYY-MM-DD` | 无 | 开始日期 |
| `end` | `YYYY-MM-DD` | 无 | 结束日期 |
| `refresh` | `bool` | `false` | 强制从akshare刷新 |

返回格式：
```json
[
  {
    "ex_date": "2025-06-15",
    "cash_dividend": 2.0,
    "stock_dividend": 0.3,
    "capitalization": 0.7,
    "rights_ratio": null,
    "rights_price": null,
    "event_type": "dividend"
  }
]
```

### 基本面数据（v2，推荐）

`GET /v2/financial/{symbol}`

按报告期获取完整基本面数据（合并每股指标、资产负债表、利润表、现金流量表、财务指标、持仓等6张表）。数据源为离线TDX数据，无需 `refresh`。

| 参数 | 类型 | 默认值 | 说明 |
|-------|------|--------|------|
| `start` | `YYYY-MM-DD` | 无 | 开始日期 |
| `end` | `YYYY-MM-DD` | 无 | 结束日期 |

返回格式——扁平结构，所有字段与查询参数中的可选列对齐：
```json
[
  {
    "symbol": "SH.600519",
    "report_date": "2025-09-30",
    "eps": 42.5,
    "bps": 185.3,
    "roe": 15.2,
    "debt_ratio": 16.8,
    "revenue": 1.23e10,
    "total_assets": 2.5e9,
    "total_liabilities": 4.2e8,
    "op_cf": 8.5e8
  }
]
```

### 选股筛选（v2）

`GET /v2/financial/query`

跨股票筛选——基于财务指标组合（ROE、负债率、EPS等）筛选符合条件的股票，每个参数同时支持 `_min` 和 `_max`。

| 参数 | 类型 | 默认值 | 说明 |
|-------|------|--------|------|
| `report_date` | `YYYY-MM-DD` | 无 | 筛选指定报告期 |
| `roe_min` / `roe_max` | `float` | 无 | ROE范围（净资产收益率） |
| `debt_ratio_min` / `debt_ratio_max` | `float` | 无 | 资产负债率范围 |
| `eps_min` / `eps_max` | `float` | 无 | 基本每股收益范围 |
| `revenue_growth_min` / `revenue_growth_max` | `float` | 无 | 营业收入增长率范围 |
| `net_profit_growth_min` / `net_profit_growth_max` | `float` | 无 | 净利润增长率范围 |
| `gross_margin_min` / `gross_margin_max` | `float` | 无 | 毛利率范围 |
| `current_ratio_min` / `current_ratio_max` | `float` | 无 | 流动比率范围 |
| `roa_min` / `roa_max` | `float` | 无 | ROA范围（总资产收益率） |

返回格式与 `/v2/financial/{symbol}` 相同（扁平结构）。

### 个股新闻

`GET /news/{symbol}`

获取个股相关新闻。

| 参数 | 类型 | 默认值 | 说明 |
|-------|------|--------|------|
| `start` | `YYYY-MM-DDThh:mm:ss` | 无 | 开始时间 |
| `end` | `YYYY-MM-DDThh:mm:ss` | 无 | 结束时间 |
| `refresh` | `bool` | `false` | 强制从akshare刷新 |

返回格式：
```json
[
  {
    "symbol": "SH.600519",
    "title": "茅台涨价提振业绩",
    "content": "...",
    "publish_time": "2026-03-20T10:30:00",
    "source_name": "东方财富",
    "url": "https://..."
  }
]
```

## Python 示例

```python
import requests

BASE = "http://localhost:8000"

# 获取前复权K线数据
kline = requests.get(
    f"{BASE}/kline/SH.600519",
    params={"start": "2025-01-01", "end": "2025-12-31", "adjust": "qfq"},
).json()

# 获取K线 + 技术指标（MA5, MA10, MACD）
kline_with_indicators = requests.get(
    f"{BASE}/indicators/SH.600519",
    params={"start": "2025-01-01", "end": "2025-12-31", "i": ["ma:5", "ma:10", "macd"]},
).json()

# 获取基本面数据（v2，合并6张表）
financial = requests.get(
    f"{BASE}/v2/financial/SH.600519",
    params={"start": "2024-01-01", "end": "2025-12-31"},
).json()

# 选股筛选：ROE > 15% 且 负债率 < 50%
screened = requests.get(
    f"{BASE}/v2/financial/query",
    params={"report_date": "2025-09-30", "roe_min": 15, "debt_ratio_max": 50},
).json()

# 获取交易日历
calendar = requests.get(
    f"{BASE}/calendar",
    params={"start": "2026-01-01", "end": "2026-03-31"},
).json()
```

## 使用场景

1. **K线技术分析** → `GET /kline/{symbol}` 获取纯K线数据，`GET /indicators/{symbol}` 获取K线+技术指标（MA/MACD/RSI/BOLL/KDJ等）
2. **基本面分析** → `GET /v2/financial/{symbol}` 一次性获取完整财务数据（合并6张表）
3. **选股筛选** → `GET /v2/financial/query` 按ROE/负债率/EPS等指标组合筛选
4. **事件驱动研究** → `GET /dividend/{symbol}` 查看分红送配历史
5. **情绪面参考** → `GET /news/{symbol}` 获取近期新闻报道

谨慎使用 `refresh=true`——仅适用于 `/dividend/{symbol}` 和 `/news/{symbol}` 端点。v2 基本面数据为离线数据，无需刷新。

## 使用规则

- 需要中国A股数据进行分析时使用本技能
- 此处列出的所有路由为 CandleX 的全部功能，不涉及组合管理、交易或用户认证
- 股票代码格式严格：`SH.600519`、`SZ.000001`、`BJ.430047`，不接受裸代码
- 复权参数（`qfq`/`hfq`）适用于 `/kline/{symbol}` 和 `/indicators/{symbol}`
- 历技术指标通过 `i` 参数指定（可重复），支持简写 `ma:5` 和 JSON 两种格式
