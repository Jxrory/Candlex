# Trading Calendar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add trading calendar cache and date correction to avoid unnecessary akshare calls on non-trading days

**Architecture:** New trade_calendar DB table (hypertable) + CalendarService with in-memory sorted date set + date correction in existing get_kline service + new /calendar endpoint

**Tech Stack:** Python 3.11+, FastAPI, asyncpg, akshare, TimescaleDB 2.27

---

### Task 1: Database Schema

**Files:**
- Modify: `scripts/init_db.sql`

- [ ] **Step 1: Add trade_calendar table**

Append to `scripts/init_db.sql`:

```sql
CREATE TABLE IF NOT EXISTS trade_calendar (
    trade_date  DATE  PRIMARY KEY,
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

SELECT create_hypertable('trade_calendar', 'trade_date', if_not_exists => TRUE);
```

- [ ] **Step 2: Commit**

```bash
git add -A && git commit -m "feat: add trade_calendar table schema"
```

---

### Task 2: CalendarService

**Files:**
- Create: `app/calendar.py`

- [ ] **Step 1: Create calendar.py**

```python
import bisect
import logging
from datetime import date

import akshare as ak
import asyncpg
import pandas as pd

from app.config import settings
from app.database import get_pool

logger = logging.getLogger(__name__)


class CalendarService:
    def __init__(self):
        self._dates: list[date] = []

    @property
    def dates(self) -> list[date]:
        return self._dates

    async def load(self) -> None:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT trade_date FROM trade_calendar ORDER BY trade_date"
            )
        if rows:
            self._dates = [r["trade_date"] for r in rows]
            logger.info("calendar loaded %d trading days from DB", len(self._dates))
        else:
            logger.info("calendar empty, fetching from akshare")
            await self._sync(pool)
        logger.info("calendar ready: %s ~ %s (%d days)",
                     self._dates[0], self._dates[-1], len(self._dates))

    async def ensure_fresh(self) -> None:
        today = date.today()
        if self._dates and self._dates[-1] >= today:
            return
        logger.info("calendar stale (last: %s), refreshing from akshare", self._dates[-1] if self._dates else "N/A")
        pool = await get_pool()
        await self._sync(pool)

    async def _sync(self, pool: asyncpg.Pool) -> None:
        df = ak.tool_trade_date_hist_sina()
        rows = [(d,) for d in df["trade_date"]]
        async with pool.acquire() as conn:
            await conn.executemany(
                "INSERT INTO trade_calendar (trade_date, updated_at) VALUES ($1, NOW()) ON CONFLICT (trade_date) DO UPDATE SET updated_at=NOW()",
                rows,
            )
        self._dates = sorted(df["trade_date"].tolist())
        logger.info("calendar synced %d trading days", len(self._dates))

    def nearest_forward(self, d: date) -> date:
        idx = bisect.bisect_right(self._dates, d)
        if idx == 0:
            return self._dates[0]
        if idx <= len(self._dates):
            prev = self._dates[idx - 1]
            return prev if prev == d else self._dates[idx]
        return d

    def nearest_backward(self, d: date) -> date:
        idx = bisect.bisect_left(self._dates, d)
        if idx == len(self._dates):
            return self._dates[-1]
        if self._dates[idx] == d:
            return d
        return self._dates[idx - 1] if idx > 0 else d

    def get_range(self, start: date, end: date) -> list[date]:
        lo = bisect.bisect_left(self._dates, start)
        hi = bisect.bisect_right(self._dates, end)
        return self._dates[lo:hi]


calendar_service = CalendarService()
```

- [ ] **Step 2: Commit**

```bash
git add -A && git commit -m "feat: add CalendarService with in-memory trading day cache"
```

---

### Task 3: Integrate Calendar into Existing Router + Service

**Files:**
- Modify: `app/service.py` — add date correction in get_kline
- Modify: `app/router.py` — add /calendar endpoint
- Modify: `app/main.py` — load calendar on startup

- [ ] **Step 1: Update service.py — add date correction**

Add import at top:

```python
from app.calendar import calendar_service
```

Insert at the beginning of `get_kline()`, after `today = date.today()`:

```python
    await calendar_service.ensure_fresh()
    start = calendar_service.nearest_forward(start)
    end = calendar_service.nearest_backward(end)
```

- [ ] **Step 2: Update router.py — add /calendar endpoint**

Add import:

```python
from app.calendar import calendar_service
```

Add new endpoint:

```python
@router.get("/calendar", response_model=list[date])
async def calendar(
    start: date | None = Query(None),
    end: date | None = Query(None),
):
    today = date.today()
    if end is None:
        end = date(today.year, 12, 31)
    if start is None:
        start = date(today.year, 1, 1)
    return calendar_service.get_range(start, end)
```

- [ ] **Step 3: Update main.py — load calendar on startup**

Add import:

```python
from app.calendar import calendar_service
```

Add before `logger.info("CandleX starting up")`:

```python
    await calendar_service.load()
```

- [ ] **Step 4: Commit**

```bash
git add -A && git commit -m "feat: integrate trading calendar into kline service and add /calendar endpoint"
```

---

### Task 4: Tests

**Files:**
- Create: `tests/test_calendar.py`

- [ ] **Step 1: Create test_calendar.py**

```python
from datetime import date
import pytest

from app.calendar import CalendarService


@pytest.fixture
def cal():
    svc = CalendarService()
    svc._dates = [
        date(2026, 1, 5), date(2026, 1, 6), date(2026, 1, 7),
        date(2026, 1, 8), date(2026, 1, 9),
        date(2026, 1, 12), date(2026, 1, 13),
    ]
    return svc


def test_nearest_forward_exact(cal):
    assert cal.nearest_forward(date(2026, 1, 5)) == date(2026, 1, 5)


def test_nearest_forward_weekend(cal):
    # Saturday 2026-01-10 -> Monday 2026-01-12
    assert cal.nearest_forward(date(2026, 1, 10)) == date(2026, 1, 12)


def test_nearest_forward_before_all(cal):
    assert cal.nearest_forward(date(2026, 1, 1)) == date(2026, 1, 5)


def test_nearest_backward_exact(cal):
    assert cal.nearest_backward(date(2026, 1, 5)) == date(2026, 1, 5)


def test_nearest_backward_weekend(cal):
    # Saturday 2026-01-10 -> Friday 2026-01-09
    assert cal.nearest_backward(date(2026, 1, 10)) == date(2026, 1, 9)


def test_nearest_backward_after_all(cal):
    assert cal.nearest_backward(date(2026, 1, 31)) == date(2026, 1, 13)


def test_get_range(cal):
    result = cal.get_range(date(2026, 1, 5), date(2026, 1, 12))
    assert result == [
        date(2026, 1, 5), date(2026, 1, 6), date(2026, 1, 7),
        date(2026, 1, 8), date(2026, 1, 9), date(2026, 1, 12),
    ]
```

- [ ] **Step 2: Run tests**

```bash
python -m pytest tests/test_calendar.py -v
```

Expected: 7 passed

- [ ] **Step 3: Run all tests**

```bash
python -m pytest tests/ -v
```

- [ ] **Step 4: Commit**

```bash
git add -A && git commit -m "test: add calendar service unit tests"
```
