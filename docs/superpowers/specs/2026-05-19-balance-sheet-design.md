# Balance Sheet Endpoint Design

**Goal:** Add `GET /balance/{symbol}` endpoint caching quarterly balance sheet data from East Money via akshare.

**Pattern:** Identical to `/indicator/{symbol}` — DB-first query, akshare fetch only on `refresh=true`.

## Route

```
GET /balance/{symbol}?start=&end=&refresh=
```

- `symbol`: `^(SH|SZ|BJ)\.[0-9]{6}$` (same validation as other routes)
- `start`/`end`: date range filter on `report_date`
- `refresh`: if `true`, re-fetch from akshare then return

## Schema

```sql
CREATE TABLE IF NOT EXISTS balance_sheets (
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
| `scripts/init_db.sql` | Append DDL | `balance_sheets` table |
| `app/schemas.py` | Add model | `BalanceSheetRecord(symbol, report_date, data)` |
| `app/sources/balance_sheet.py` | Create | `BalanceSheetSource` — wraps `ak.stock_balance_sheet_by_report_em` |
| `app/balance_sheet.py` | Create | `BalanceSheetService` — `get_balance_sheets()` + `sync_symbol()` |
| `app/router.py` | Add route | `GET /balance/{symbol}` |
| `app/ak_trace.py` | Add case | `_extract_params` handling for `stock_balance_sheet_by_report_em` |
| `tests/test_balance_sheet.py` | Create | Unit + route tests |

## Key Detail: Symbol Format

The akshare API expects `SH600519` (no dot, uppercase market prefix). The app internally uses `SH.600519`. Conversion:

```python
def _to_raw_code(self, symbol: str) -> str:
    return symbol.replace(".", "")
```

## Data Flow

```
Request → router → service.get_balance_sheets()
  ├─ DB hit → return cached records (if no refresh)
  └─ refresh=true → source.fetch() → akshare → upsert DB → return
```

## Trace

`stock_balance_sheet_by_report_em` must be added to `_extract_params` in `ak_trace.py` to capture `symbol` param (passed as positional arg in `_fetch`).
