# Auto-Sync on Empty Cache Design

**Goal:** When `refresh=false` and a DB query returns no data, automatically call `sync_symbol` and re-query.

## Scope

6 endpoints in `app/router.py`:

| Route | Service | get method | sync method |
|---|---|---|---|
| `/indicator/{symbol}` | `financial_indicator_service` | `get_indicators` | `sync_symbol` |
| `/balance/{symbol}` | `balance_sheet_service` | `get_balance_sheets` | `sync_symbol` |
| `/profit/{symbol}` | `profit_sheet_service` | `get_profit_sheets` | `sync_symbol` |
| `/cash-flow/{symbol}` | `cash_flow_sheet_service` | `get_cash_flow_sheets` | `sync_symbol` |
| `/news/{symbol}` | `news_service` | `get_news` | `sync_symbol` |
| `/dividend/{symbol}` | `dividend_service` | `get_events` | `sync_symbol` |

## Behavioral Change

Current:
```
if refresh → sync
query → return
```

New:
```
if refresh → sync
query
if empty and not refresh → sync + query again
return
```

## Files Changed

Only `app/router.py` — each of the 6 handlers gets a `if not records and not refresh:` block between the first query and the return.

## No New Dependencies

No schema changes, no new imports, no new files.
