# Kline Sync Cron — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A scheduled task that backfills daily K-line data (2000-01-01 to yesterday) for each A-share stock with `list_status IS NULL`, then marks it synced.

**Architecture:** New `KlineSyncService` module (sequential per-stock processing). Scheduler in `main.py` runs it on a random 5–13 minute interval, rescheduling after each run with jitter. Only SZ/SH symbols (by prefix), BJ excluded.

**Tech Stack:** FastAPI, APScheduler, asyncpg, existing `service.get_kline()`

---

## Files

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `app/kline_sync.py` | `KlineSyncService.sync_all()` — query pending stocks, call `get_kline`, mark synced |
| Modify | `app/config.py` | Add `kline_sync_interval` setting (default 540) |
| Modify | `app/main.py` | Add `sync_kline` job with random interval rescheduling |
| Create | `tests/test_kline_sync.py` | Unit tests for sync logic |

---

### Task 1: Create `app/kline_sync.py`

**Files:**
- Create: `app/kline_sync.py`
- Test: `tests/test_kline_sync.py`

- [ ] **Step 1: Write the failing tests**

```python
import pytest
from datetime import date, timedelta
from unittest.mock import AsyncMock, patch

from app.kline_sync import KlineSyncService

Y2000 = date(2000, 1, 1)
TODAY = date.today()
YESTERDAY = TODAY - timedelta(days=1)


@pytest.mark.asyncio
async def test_sync_all_success():
    """Stocks with list_status IS NULL are synced and marked."""
    pool = AsyncMock()
    conn = pool.acquire.return_value.__aenter__.return_value
    conn.fetch.return_value = [{"symbol": "SH.600519"}]
    conn.execute.return_value = "UPDATE 1"

    with patch("app.kline_sync.get_kline", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = []
        result = await KlineSyncService().sync_all(pool)

    mock_get.assert_called_once_with("SH.600519", Y2000, YESTERDAY)
    conn.execute.assert_called_once_with(
        "UPDATE stock_info SET list_status = 'SYNCED', list_date = NOW() WHERE symbol = $1",
        "SH.600519",
    )
    assert result == 1


@pytest.mark.asyncio
async def test_no_pending_stocks():
    """If no stocks are pending, returns 0 and does nothing."""
    pool = AsyncMock()
    pool.acquire.return_value.__aenter__.return_value.fetch.return_value = []

    with patch("app.kline_sync.get_kline", new_callable=AsyncMock) as mock_get:
        result = await KlineSyncService().sync_all(pool)

    mock_get.assert_not_called()
    assert result == 0


@pytest.mark.asyncio
async def test_failure_skips_and_continues():
    """Failed stock is not marked SYNCED; next stock continues."""
    pool = AsyncMock()
    conn = pool.acquire.return_value.__aenter__.return_value
    conn.fetch.return_value = [
        {"symbol": "SH.600519"},
        {"symbol": "SZ.000001"},
    ]
    conn.execute.return_value = "UPDATE 1"

    with patch("app.kline_sync.get_kline", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = [Exception("network error"), []]
        result = await KlineSyncService().sync_all(pool)

    assert mock_get.call_count == 2
    conn.execute.assert_called_once_with(
        "UPDATE stock_info SET list_status = 'SYNCED', list_date = NOW() WHERE symbol = $1",
        "SZ.000001",
    )
    assert result == 1


@pytest.mark.asyncio
async def test_only_sz_sh():
    """Only SZ and SH symbols are queried."""
    pool = AsyncMock()
    conn = pool.acquire.return_value.__aenter__.return_value
    conn.fetch.return_value = [
        {"symbol": "SH.600519"},
        {"symbol": "SZ.000001"},
        {"symbol": "SZ.300750"},
    ]
    conn.execute.return_value = "UPDATE 1"

    with patch("app.kline_sync.get_kline", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = []
        await KlineSyncService().sync_all(pool)

    conn.fetch.assert_called_once()
    sql = conn.fetch.call_args[0][0]
    assert "LIKE 'SH.%'" in sql or "LIKE 'SZ.%'" in sql
    assert "LIKE 'BJ.%'" not in sql
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_kline_sync.py -v
```
Expected: 4 FAILED (cannot import `KlineSyncService`)

- [ ] **Step 3: Write minimal implementation**

```python
import logging
from datetime import date, timedelta

import asyncpg

from app.service import get_kline

logger = logging.getLogger(__name__)

Y2000 = date(2000, 1, 1)


class KlineSyncService:

    async def sync_all(self, pool: asyncpg.Pool) -> int:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT symbol FROM stock_info "
                "WHERE (symbol LIKE 'SH.%' OR symbol LIKE 'SZ.%') "
                "AND list_status IS NULL"
            )
        symbols = [r["symbol"] for r in rows]
        if not symbols:
            logger.info("no stocks pending kline sync")
            return 0

        yesterday = date.today() - timedelta(days=1)
        count = 0
        for symbol in symbols:
            try:
                records = await get_kline(symbol, Y2000, yesterday)
                async with pool.acquire() as conn:
                    await conn.execute(
                        "UPDATE stock_info SET list_status = 'SYNCED', list_date = NOW() WHERE symbol = $1",
                        symbol,
                    )
                logger.info("synced kline for %s (%d rows)", symbol, len(records))
                count += 1
            except Exception as e:
                logger.error("kline sync failed for %s: %s", symbol, e)
        return count


kline_sync_service = KlineSyncService()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_kline_sync.py -v
```
Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
git add app/kline_sync.py tests/test_kline_sync.py
git commit -m "feat: add KlineSyncService for backfilling kline data"
```

---

### Task 2: Add config for sync interval

**Files:**
- Modify: `app/config.py`

- [ ] **Step 1: Add `kline_sync_interval` setting**

Insert after `dividend_sync_symbols: list[str] = []` in `app/config.py:18`:

```python
kline_sync_interval: int = 540
```

- [ ] **Step 2: Verify no existing tests break**

```bash
pytest tests/test_config.py -v 2>/dev/null || echo "no config tests"
```

- [ ] **Step 3: Commit**

```bash
git add app/config.py
git commit -m "feat: add kline_sync_interval config (default 540s)"
```

---

### Task 3: Schedule the job in `main.py`

**Files:**
- Modify: `app/main.py`

- [ ] **Step 1: Add import and sync function before `lifespan`**

Add `import random` next to `import asyncio` at the top of the file (line 1 area), then insert the `sync_kline` function after `sync_spot_snapshot` (after line 65):

```python
async def sync_kline():
    logger.info("scheduled task: sync kline for pending stocks")
    pool = await get_pool()
    try:
        count = await kline_sync_service.sync_all(pool)
        logger.info("scheduled task: synced kline for %d stocks", count)
    except Exception as e:
        logger.error("scheduled task: kline sync failed: %s", e)

    next_interval = random.randint(300, 780)
    scheduler.reschedule_job(
        "sync_kline",
        trigger="interval",
        seconds=next_interval,
    )
    logger.info("scheduled task: next kline sync in %d seconds", next_interval)
```

- [ ] **Step 2: Add scheduler job in `lifespan`**

Inside `lifespan`, after the `sync_spot_snapshot` job is added (after line 103), before `scheduler.start()`:

```python
    scheduler.add_job(
        sync_kline,
        trigger="interval",
        seconds=random.randint(300, 780),
        id="sync_kline",
        replace_existing=True,
    )
```

Note: `import random` was added at the top of the file alongside `import asyncio`.

- [ ] **Step 3: Verify syntax**

```bash
python -c "from app.main import app; print('OK')"
```
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add app/main.py
git commit -m "feat: schedule kline sync cron with random 5-13 min interval"
```

---

### Self-Review Checklist

| Spec Requirement | Covered By |
|------------------|------------|
| Fetch stocks from stock_info with list_status IS NULL | Task 1, Step 3 SQL query |
| Only SZ/SH (by symbol prefix) | Task 1, Step 3 `LIKE 'SH.%' OR LIKE 'SZ.%'` |
| Use get_kline for each stock | Task 1, Step 3 calls `get_kline` |
| Date range 2000-01-01 to yesterday | Task 1, Step 3 `Y2000` and `date.today() - timedelta(days=1)` |
| On success, backfill list_status and list_date | Task 1, Step 3 UPDATE |
| On failure, log and continue, no mark | Task 1, Step 3 try/except pattern |
| Interval 5-13 min (random) | Task 3, Step 1 `random.randint(300, 780)` |
| Sequential execution | Task 1, Step 3 for-loop, no concurrency |
