# Profit Sheet Endpoint Design

**Goal:** Add `GET /profit/{symbol}` endpoint caching quarterly profit sheet data from East Money via akshare.

**Pattern:** Identical to `/balance/{symbol}` — DB-first query, akshare fetch only on `refresh=true`.

## Route

```
GET /profit/{symbol}?start=&end=&refresh=
```

## Schema

```sql
CREATE TABLE IF NOT EXISTS profit_sheets (
    symbol       TEXT    NOT NULL,
    report_date  DATE    NOT NULL,
    data         JSONB   NOT NULL,
    source       TEXT    NOT NULL,
    updated_at   TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (symbol, report_date)
);
```

## Files

| File | Action | Role |
|------|--------|------|
| `scripts/init_db.sql` | Append DDL | `profit_sheets` table |
| `app/schemas.py` | Add model | `ProfitSheetRecord` |
| `app/sources/profit_sheet.py` | Create | `ProfitSheetSource` |
| `app/profit_sheet.py` | Create | `ProfitSheetService` |
| `app/router.py` | Add route | `GET /profit/{symbol}` |
| `app/ak_trace.py` | Add case | `_extract_params` for `stock_profit_sheet_by_report_em` |
| `tests/test_profit_sheet.py` | Create | Unit + route tests |
