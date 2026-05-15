# Stock List Service — Design Spec

## 1. Goal

Add a stock list caching endpoint and monthly sync scheduler for Chinese A-shares, with extensibility for HK/US markets.

## 2. Database Table

```sql
CREATE TABLE IF NOT EXISTS stock_info (
    symbol       TEXT   NOT NULL PRIMARY KEY,
    name         TEXT   NOT NULL,
    market       TEXT   NOT NULL,       -- ZH_A | HK | US
    list_date    DATE,
    list_status  TEXT,                  -- L / D / etc
    industry     TEXT,                  -- 申万行业
    sector       TEXT,                  -- 板块
    updated_at   TIMESTAMPTZ DEFAULT NOW()
);
```

- Regular table — not a hypertable (metadata, not time-series).
- Primary key: `symbol`.

## 3. Data Source

### ZH_A (A-share)

Primary: `ak.stock_info_a_code_name()` — returns all A-share stocks (SH/SZ/BJ) with `code` + `name`.

Secondary (best-effort): `ak.stock_individual_info()` per code — may return list_date, industry. On failure → skip, leave null.

### HK / US

Placeholder — the source class returns an empty DataFrame. No API calls.

## 4. API Route

```
GET /stocks
```

Query parameters:

| Param    | Type    | Default | Description |
|----------|---------|---------|-------------|
| market   | str     | None    | Filter: ZH_A / HK / US. None = all. |
| refresh  | bool    | False   | Re-fetch from akshare if true. |

Response: `list[StockInfoRecord]`

- If `refresh=false` (default), query DB only.
- If `refresh=true`, call `StockListService.sync(market)`, then return from DB.

## 5. Scheduler

Monthly on the 15th at 08:30:

```python
scheduler.add_job(
    sync_stock_list,
    trigger="cron",
    day=15,
    hour=8,
    minute=30,
    id="sync_stock_list",
    replace_existing=True,
)
```

Currently only syncs `ZH_A`. Extensible to `HK`, `US` later.

## 6. Code Structure

```
app/
├── stock_list.py          # StockListService (DB ops + orchestration)
└── sources/
    └── stock_list.py      # StockListSource (akshare calls)
```

- `StockListService` — analogous to `DividendService`; uses `get_pool()` for DB.
- `StockListSource` — has a `fetch(market)` method returning a DataFrame.

## 7. Schema

```python
class StockInfoRecord(BaseModel):
    symbol: str
    name: str
    market: str
    list_date: date | None = None
    list_status: str | None = None
    industry: str | None = None
    sector: str | None = None
```

## 8. Testing

- `test_stock_list.py`: unit tests for `StockListSource` (ZH_A fetch), service logic, route integration.
- Real akshare calls are integration-level; DB-dependent tests follow existing pattern.
- Test the scheduled job registration exists (not execution).

## 9. Config

No new env vars required. The scheduler time can reuse or extend existing patterns.
