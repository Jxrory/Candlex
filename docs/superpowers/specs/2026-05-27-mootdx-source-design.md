# mootdx K-Line Data Source

## Motivation

Add `mootdx` as an additional K-line data source for CandleX's multi-source failover chain. mootdx connects directly to TDX (通达信) servers, providing an alternative to akshare-based sources (Sina, Tencent, EastMoney).

## Scope

Minimal change: new source file + registration in `SOURCES` dict. No new dependencies (already in `pyproject.toml`). No config changes needed (existing `source_priority` mechanism applies).

## Design

### Source file: `app/sources/mootdx.py`

- Implements `BaseSource` (`name = "mootdx"`, `async fetch(...)`)
- Parses symbol: `symbol.split(".")[1]` extracts bare 6-digit code (e.g., `600300`), same as EastMoney
- Uses `run_in_executor` to wrap synchronous `Quotes.factory(market='std').k(...)` call
- Returns DataFrame with columns: `date`, `open`, `high`, `low`, `close`, `volume`, `amount`
- `vol` field (in lots) × 100 → `volume` (shares), matching existing schema
- Logging via `logger.info/warning` directly (no `@trace_akshare`)

### Registration: `app/service.py`

Add `MootdxSource` to the `SOURCES` dict. Existing failover logic (`source_priority`) handles it automatically.

### Symbol format compatibility

| Source | Input example | API format |
|--------|--------------|------------|
| Sina | `SH.600519` | `sh600519` |
| Tencent | `SH.600519` | `sh600519` |
| EastMoney | `SH.600519` | `600519` |
| **mootdx** | `SH.600519` | `600519` |

### Data mapping

| mootdx column | Our column | Notes |
|---------------|-----------|-------|
| `date` (index) | `date` | |
| `open` | `open` | |
| `high` | `high` | |
| `low` | `low` | |
| `close` | `close` | |
| `vol` | `volume` | × 100 (手 → 股数) |
| `amount` | `amount` | |

## Files changed

1. `app/sources/mootdx.py` — new file
2. `app/service.py` — add import + register in `SOURCES`
