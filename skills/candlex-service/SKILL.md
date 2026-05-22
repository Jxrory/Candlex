---
name: candlex-service
description: 使用场景：需要获取中国A股市场数据时——包括K线OHLCV、交易日历、分红/公司事件、财务报表（资产负债表/利润表/现金流量表）、财务指标、股票列表、个股新闻。基于akshare多源故障转移的缓存优先只读API。
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

### 财务指标

`GET /indicator/{symbol}`

ROE、EPS等关键财务比率指标，按报告期提供。

| 参数 | 类型 | 默认值 | 说明 |
|-------|------|--------|------|
| `start` | `YYYY-MM-DD` | 无 | 开始日期 |
| `end` | `YYYY-MM-DD` | 无 | 结束日期 |
| `refresh` | `bool` | `false` | 强制从akshare刷新 |

返回格式：
```json
[
  {
    "symbol": "SH.600519",
    "report_date": "2025-09-30",
    "data": { "roe": 15.2, "eps": 42.5, "bps": 185.3 }
  }
]
```

### 资产负债表

`GET /balance/{symbol}`

按报告期获取资产负债表。

| 参数 | 类型 | 默认值 | 说明 |
|-------|------|--------|------|
| `start` | `YYYY-MM-DD` | 无 | 开始日期 |
| `end` | `YYYY-MM-DD` | 无 | 结束日期 |
| `refresh` | `bool` | `false` | 强制从akshare刷新 |

返回格式：
```json
[
  {
    "symbol": "SH.600519",
    "report_date": "2025-09-30",
    "data": { "total_assets": 2.5e9, "total_liabilities": 4.2e8 }
  }
]
```

### 利润表（损益表）

`GET /profit/{symbol}`

按报告期获取利润表。

| 参数 | 类型 | 默认值 | 说明 |
|-------|------|--------|------|
| `start` | `YYYY-MM-DD` | 无 | 开始日期 |
| `end` | `YYYY-MM-DD` | 无 | 结束日期 |
| `refresh` | `bool` | `false` | 强制从akshare刷新 |

返回格式：与 `/balance/{symbol}` 结构相同。

### 现金流量表

`GET /cash-flow/{symbol}`

按报告期获取现金流量表。

| 参数 | 类型 | 默认值 | 说明 |
|-------|------|--------|------|
| `start` | `YYYY-MM-DD` | 无 | 开始日期 |
| `end` | `YYYY-MM-DD` | 无 | 结束日期 |
| `refresh` | `bool` | `false` | 强制从akshare刷新 |

返回格式：与 `/balance/{symbol}` 结构相同。

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

# 获取财务指标，强制刷新
indicators = requests.get(
    f"{BASE}/indicator/SH.600519",
    params={"refresh": "true"},
).json()

# 获取交易日历
calendar = requests.get(
    f"{BASE}/calendar",
    params={"start": "2026-01-01", "end": "2026-03-31"},
).json()
```

## 使用场景

1. **K线技术分析** → `GET /kline/{symbol}`，可按需使用 `adjust` 参数复权
2. **基本面分析** → 组合使用 `GET /indicator/{symbol}` + `GET /balance/{symbol}` + `GET /profit/{symbol}` + `GET /cash-flow/{symbol}`
3. **事件驱动研究** → `GET /dividend/{symbol}` 查看分红送配历史
5. **情绪面参考** → `GET /news/{symbol}` 获取近期新闻报道

谨慎使用 `refresh=true`——数据会自动缓存到TimescaleDB并在首次访问时获取。仅在需要同一会话内最新数据时才传 `refresh`。

## 使用规则

- 需要中国A股数据进行分析时使用本技能
- 此处列出的所有路由为 CandleX 的全部功能，不涉及组合管理、交易或用户认证
- 股票代码格式严格：`SH.600519`、`SZ.000001`、`BJ.430047`，不接受裸代码
- 复权参数（`qfq`/`hfq`）仅适用于 `/kline/{symbol}`
