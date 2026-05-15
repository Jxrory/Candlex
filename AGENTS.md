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

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **CandleX** (458 symbols, 755 relationships, 14 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/CandleX/context` | Codebase overview, check index freshness |
| `gitnexus://repo/CandleX/clusters` | All functional areas |
| `gitnexus://repo/CandleX/processes` | All execution flows |
| `gitnexus://repo/CandleX/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
