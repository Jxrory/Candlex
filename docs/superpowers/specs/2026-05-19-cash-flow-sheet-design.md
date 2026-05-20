# Cash Flow Sheet Endpoint Design

**Goal:** Add `GET /cash-flow/{symbol}` endpoint caching quarterly cash flow sheet data via `ak.stock_cash_flow_sheet_by_report_em`.

**Pattern:** Identical to `/balance/{symbol}`.

## Route

```
GET /cash-flow/{symbol}?start=&end=&refresh=
```

## Schema

```sql
CREATE TABLE IF NOT EXISTS cash_flow_sheets (
    symbol       TEXT    NOT NULL,
    report_date  DATE    NOT NULL,
    data         JSONB   NOT NULL,
    source       TEXT    NOT NULL,
    updated_at   TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (symbol, report_date)
);
```
