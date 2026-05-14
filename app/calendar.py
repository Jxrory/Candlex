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
        logger.info("calendar stale (last: %s), refreshing", self._dates[-1] if self._dates else "N/A")
        pool = await get_pool()
        await self._sync(pool)

    async def _sync(self, pool: asyncpg.Pool) -> None:
        logger.info("fetching trading calendar from akshare")
        df = ak.tool_trade_date_hist_sina()
        logger.info("akshare returned %d trading days, columns=%s", len(df), list(df.columns))
        rows = [(d,) for d in df["trade_date"]]
        logger.info("calendar upsert starting (%d rows)...", len(rows))
        if rows:
            logger.info("first 3 rows: %s, last row: %s", rows[:3], rows[-1])
        async with pool.acquire() as conn:
            await conn.executemany(
                "INSERT INTO trade_calendar (trade_date, updated_at) VALUES ($1, NOW()) ON CONFLICT (trade_date) DO UPDATE SET updated_at=NOW()",
                rows,
                timeout=120,
            )
        self._dates = sorted(df["trade_date"].tolist())
        logger.info("calendar synced %d trading days: %s ~ %s",
                     len(self._dates), self._dates[0], self._dates[-1])

    def nearest_forward(self, d: date) -> date:
        idx = bisect.bisect_right(self._dates, d)
        if idx == 0:
            return self._dates[0]
        if idx < len(self._dates):
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
