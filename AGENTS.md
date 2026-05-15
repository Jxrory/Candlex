# CandleX

Daily K-line caching service for Chinese A-stocks, using akshare with multi-source failover.

## Quick start

```bash
pip install -e ".[dev]"
uvicorn app.main:app    # runs on :8000
pytest                  # asyncio_mode=auto, no extra flags needed
pytest tests/test_foo.py -k test_name
```

## Architecture

- **FastAPI** app with `async` lifespan — no `lifespan` context is used (the `lifespan` async generator in `main.py` handles startup/shutdown directly).
- **asyncpg** connection pool (singleton via `get_pool()`, lazy-init with double-checked locking).
- **TimescaleDB** required — 4 hypertables (`kline_data`, `corporate_events`, `trade_calendar`, `api_request_log`).
- **No ORM** — raw SQL with `$1, $2` param style for asyncpg.

## Key structure

| Path | Role |
|------|------|
| `app/main.py` | App entrypoint, scheduler setup (dividend sync cron **currently commented out**) |
| `app/router.py` | 3 routes: `/calendar`, `/kline/{symbol}`, `/dividend/{symbol}` |
| `app/service.py` | K-line fetch with DB cache → source failover → dividend adjustment |
| `app/calendar.py` | Trading calendar (bisect-based nearest-day lookup) |
| `app/dividend.py` | Corporate events (dividends, rights issues) with adjustment factor calc |
| `app/ak_trace.py` | `@trace_akshare("api_name")` decorator — logs akshare calls to `api_request_log` via async queue writer |
| `app/sources/` | `BaseSource` ABC. `SinaSource` registered in `SOURCES` dict. `TencentSource`, `EastMoneySource` exist but **not registered** — only used if added to `SOURCES` dict. `DividendSource` is stand-alone. |

## Routes

- `/calendar?start=&end=` — list trading days in range
- `/kline/{symbol}?start=&end=&adjust=` — `symbol` must match `^(SH|SZ|BJ)\.[0-9]{6}$`; `adjust` must be `qfq` or `hfq`
- `/dividend/{symbol}?start=&end=&refresh=` — dividend events, supports `refresh=true` to re-fetch from akshare

## Data sources

`source_priority` in config (env `CANDLEX_SOURCE_PRIORITY`) controls failover order. Default: `["sina", "tencent", "eastmoney"]`. Only Sina is wired into `service.py`'s `SOURCES` dict — to use tencent/eastmoney, add them there.

## Config

`pydantic-settings`, prefix `CANDLEX_`, reads `.env`. Key vars:

| Env | Default |
|-----|---------|
| `CANDLEX_DB_DSN` | `postgresql://user:password@192.168.1.10:5432/candlex` |
| `CANDLEX_SOURCE_PRIORITY` | `["sina", "tencent", "eastmoney"]` |

## Testing quirks

- Integration tests hit real DB (no mocking) — the `test_router.py` tests make real queries.
- `test_service.py` only tests `_apply_adjust` (unit-level, no DB).
- Calendar tests use `CalendarService` with manually injected `_dates` — no DB needed.
- `test_ak_trace.py` tests the decorator/param extraction logic in isolation.
- No linter or type checker is configured. No formatter config exists.

## Symbol handling

- akshare calls use market-specific formats: Sina wants `sh600519` (lowercase, no dot); EastMoney wants bare `600519`; Tencent wants `SH600519` (no dot).
- `app/sources/dividend.py` extracts raw 6-digit code via `symbol.split(".")[1]`.
