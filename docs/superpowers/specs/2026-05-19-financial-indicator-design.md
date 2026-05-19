# Financial Indicator Service — Design Spec

## 1. Goal

Add a financial analysis indicator endpoint for Chinese A-shares, caching quarterly report data from East Money (`stock_financial_analysis_indicator_em`). DB-first — akshare is called only when `refresh=true`.

## 2. Database Table

```sql
CREATE TABLE IF NOT EXISTS financial_indicators (
    symbol       TEXT    NOT NULL,
    report_date  DATE    NOT NULL,
    data         JSONB   NOT NULL,
    source       TEXT    NOT NULL,
    updated_at   TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (symbol, report_date)
);
```

- Regular table — not a hypertable (report-period data, not per-trading-day).
- `data` stores the full API response as JSONB, preserving all indicator fields.
- Upsert via `ON CONFLICT (symbol, report_date) DO UPDATE SET data = EXCLUDED.data, source = EXCLUDED.source, updated_at = NOW()` ensures multiple `refresh=true` calls never duplicate rows.

## 3. Data Source

### API

`ak.stock_financial_analysis_indicator_em(symbol=raw_code, indicator="单季报")`

- Returns all historical single-quarter reports for a stock.
- Raw code is 6-digit (e.g., `600519`), extracted by stripping the exchange prefix from the canonical symbol (`SH.600519` → `600519`).
- Decorated with `@trace_akshare("stock_financial_analysis_indicator_em")`.

### Source file

`app/sources/financial_indicator.py` — `FinancialIndicatorSource`

- Single `fetch(symbol)` method returning a `pd.DataFrame`.
- Transforms each DataFrame row into a dict for JSONB storage.

## 4. API Route

```
GET /indicator/{symbol}
```

Query parameters:

| Param    | Type    | Default | Description                                      |
|----------|---------|---------|--------------------------------------------------|
| symbol   | path    | -       | `^(SH\|SZ\|BJ)\.[0-9]{6}$`                      |
| start    | date    | None    | Filter by report_date (inclusive)                |
| end      | date    | None    | Filter by report_date (inclusive)                |
| refresh  | bool    | False   | Re-fetch from akshare if true                    |

- If `refresh=false` (default), query DB only.
- If `refresh=true`, call `FinancialIndicatorService.sync_symbol()`, then return from DB.
- Upsert logic prevents duplicate rows on repeated refresh calls.

Response: `list[FinancialIndicatorRecord]`

```python
class FinancialIndicatorRecord(BaseModel):
    symbol: str
    report_date: date
    data: dict
```

## 5. Code Structure

```
app/
├── financial_indicator.py          # FinancialIndicatorService (DB ops + orchestration)
├── sources/
│   └── financial_indicator.py      # FinancialIndicatorSource (akshare call)
├── schemas.py                      # + FinancialIndicatorRecord
└── router.py                       # + GET /indicator/{symbol}
```

- `FinancialIndicatorService` — follows the `StockListService`/`DividendService` pattern; uses `get_pool()` for DB access.
- `FinancialIndicatorSource` — standalone source (not inheriting `BaseSource` since this endpoint doesn't use failover).

## 6. Schema

```python
class FinancialIndicatorRecord(BaseModel):
    symbol: str
    report_date: date
    data: dict
```

## 7. DB Migration

Append the `CREATE TABLE` statement to `scripts/init_db.sql`.

## 8. Testing

- `test_financial_indicator.py`:
  - Unit: source transformation logic, schema defaults.
  - Integration: route returns 200 with correct shape; `refresh=true` triggers sync path.
- Follow existing test patterns (real DB for integration, no mocking).

## 9. Config

No new env vars required.
