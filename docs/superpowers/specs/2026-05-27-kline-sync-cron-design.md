# Kline Sync Cron — Design

## Goal

A scheduled task that backfills K-line data for all A-share stocks. One-time per stock (when `list_status IS NULL`), fetching daily bars from 2000-01-01 to yesterday.

## Scope

- Only SZ and SH symbols (BJ excluded, identified by symbol prefix `SH.` / `SZ.`).
- Only stocks where `list_status IS NULL` (not yet synced).
- After successful sync, mark `list_status = 'SYNCED'` and `list_date = NOW()`.
- Failed stocks are NOT marked — they retry on next run.

## Execution

- Runs at random intervals between 5–13 minutes (randomized after each run ends).
- Stocks are processed **sequentially** (one at a time) to avoid overwhelming data sources.
- Uses existing `service.get_kline()` which handles DB cache → source failover → upsert.

## New Module: `app/kline_sync.py`

```python
class KlineSyncService:
    async def sync_all(self, pool: asyncpg.Pool) -> int
```

Flow:
1. Query `SELECT symbol FROM stock_info WHERE (symbol LIKE 'SH.%' OR symbol LIKE 'SZ.%') AND list_status IS NULL`
2. For each symbol:
   - Call `service.get_kline(symbol, date(2000, 1, 1), yesterday)`
   - On success: `UPDATE stock_info SET list_status = 'SYNCED', list_date = NOW()`
   - On exception: log error, continue to next symbol
3. Return count of successfully synced stocks

## Config Changes (`app/config.py`)

| Env | Type | Default | Description |
|-----|------|---------|-------------|
| `CANDLEX_KLINE_SYNC_INTERVAL` | `int` | `540` | Base interval in seconds (~9 min mid-point) |

The random jitter (±40% around base) is applied at the scheduler level.

## Scheduler (`app/main.py`)

- Import `kline_sync_service` and add job with `IntervalTrigger`
- After each job run, randomize next interval: `base_interval * random.uniform(0.56, 1.44)` → clamp to [300, 780]
- Re-register with `replace_existing=True`

## Testing (`tests/test_kline_sync.py`)

- Mock `service.get_kline` to test:
  - Stock with NULL list_status → gets synced and marked
  - Stock with SYNCED status → skipped
  - Failed stock → not marked, logged, continues to next
- No DB needed
