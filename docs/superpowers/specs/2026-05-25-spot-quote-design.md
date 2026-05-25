# Real-time Spot Quote API

**Goal:** Add real-time A-share market data using `ak.stock_zh_a_spot_em` with both real-time (no cache) and post-market (DB-backed) modes.

## Routes

| Method | Path | Mode | Description |
|--------|------|------|-------------|
| GET | `/quote/spot/real` | Real-time | All stocks, direct akshare call |
| GET | `/quote/spot/real/{symbol}` | Real-time | Single stock, direct akshare call |
| GET | `/quote/spot` | Post-market | All stocks, read DB latest snapshot |
| GET | `/quote/spot/{symbol}` | Post-market | Single stock, read DB latest snapshot |

`symbol` pattern: `^(SH\|SZ\|BJ)\.[0-9]{6}$`

`/quote/spot/real` supports optional `?codes=600519,000001` query param for batch filtering.

## Response

`list[dict]` — each dict contains all columns from `stock_zh_a_spot_em`:

| Field | Type | Description |
|-------|------|-------------|
| 序号 | int64 | - |
| 代码 | str | 6-digit code |
| 名称 | str | Stock name |
| 最新价 | float64 | Latest price |
| 涨跌幅 | float64 | Change % |
| 涨跌额 | float64 | Change amount |
| 成交量 | float64 | Volume (lots) |
| 成交额 | float64 | Turnover (CNY) |
| 振幅 | float64 | Amplitude % |
| 最高 | float64 | Day high |
| 最低 | float64 | Day low |
| 今开 | float64 | Day open |
| 昨收 | float64 | Previous close |
| 量比 | float64 | Volume ratio |
| 换手率 | float64 | Turnover rate % |
| 市盈率-动态 | float64 | PE (dynamic) |
| 市净率 | float64 | PB |
| 总市值 | float64 | Total market cap |
| 流通市值 | float64 | Circulating market cap |
| 涨速 | float64 | Speed |
| 5分钟涨跌 | float64 | 5min change % |
| 60日涨跌幅 | float64 | 60d change % |
| 年初至今涨跌幅 | float64 | YTD change % |

## Architecture

### Data Source — `app/sources/spot.py`

`SpotSource` wrapping `ak.stock_zh_a_spot_em`:
- `fetch_all()` → returns full market DataFrame
- `filter_symbol(df, symbol)` → filters by bare code (e.g. "600519")
- No DB interaction, no symbol param to akshare

Does not inherit `BaseSource` (same pattern as DividendSource, NewsSource).

### Service — `app/spot.py`

`SpotService` with three public methods:
- `fetch_real(symbol=None)` — calls akshare directly, no caching
- `get_latest(pool, symbol=None)` — reads latest snapshot from DB
- `sync_all(pool)` — fetches full snapshot, writes to `spot_snapshots` + `kline_data`

### DB — `spot_snapshots` table

Per-stock per-snapshot, all fields stored as JSONB:

```sql
CREATE TABLE IF NOT EXISTS spot_snapshots (
    symbol         TEXT NOT NULL,
    snapshot_time  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    data           JSONB NOT NULL,
    source         TEXT NOT NULL,
    PRIMARY KEY (symbol, snapshot_time)
);

SELECT create_hypertable('spot_snapshots', 'snapshot_time', if_not_exists => TRUE);
CREATE INDEX idx_spot_snapshots_symbol_time ON spot_snapshots (symbol, snapshot_time DESC);
```

### K-line integration

`sync_all()` also upserts today's data into `kline_data`:

| Spot field | kline_data column |
|-----------|-------------------|
| 今开 | open |
| 最高 | high |
| 最低 | low |
| 最新价 | close |
| 成交量 (手 × 100) | volume |
| 成交额 | amount |

All other `kline_data` columns (source, symbol, date) set accordingly.

### Scheduled Task — `app/main.py`

APScheduler cron at 17:00 daily (after market close):

```python
scheduler.add_job(
    sync_spot_snapshot,
    trigger="cron",
    hour=17, minute=0,
    id="sync_spot_snapshot",
    replace_existing=True,
)
```

### Trace — `app/ak_trace.py`

Add `stock_zh_a_spot_em` to `_extract_params` (no params to extract, just recognize the API name for logging).

## Files to Create/Modify

| File | Action | Content |
|------|--------|---------|
| `scripts/init_db.sql` | Append DDL | `spot_snapshots` table |
| `app/sources/spot.py` | Create | `SpotSource` wrapping `ak.stock_zh_a_spot_em` |
| `app/spot.py` | Create | `SpotService` — fetch_real, get_latest, sync_all |
| `app/router.py` | Add routes | 4 quote/spot routes |
| `app/ak_trace.py` | Add case | `_extract_params` for `stock_zh_a_spot_em` |
| `app/main.py` | Add import + job | `sync_spot_snapshot` cron at 17:00 |
| `tests/test_spot.py` | Create | Unit + route tests |

## Data Flow

### Real-time mode
```
Request → /quote/spot/real → router → SpotService.fetch_real()
  → SpotSource.fetch_all() → ak.stock_zh_a_spot_em() → list[dict]
  → filter by symbol if needed → response
```

### Post-market mode
```
Request → /quote/spot → router → SpotService.get_latest()
  → SELECT data FROM spot_snapshots WHERE snapshot_time = (SELECT MAX(...))
  → filter by symbol if needed → response
```

### Scheduled sync
```
APScheduler (17:00) → sync_spot_snapshot()
  → SpotService.sync_all(pool)
    → SpotSource.fetch_all() → ak.stock_zh_a_spot_em()
    → INSERT INTO spot_snapshots (per stock, per snapshot)
    → UPSERT INTO kline_data (today's daily bar)
```

## Testing

`tests/test_spot.py`:
- Source fetch with mocked akshare
- Service real-time mode (no DB)
- Service post-market mode (mocked pool)
- Symbol filtering
- Route integration tests
