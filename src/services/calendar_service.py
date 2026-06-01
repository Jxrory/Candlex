import bisect
import logging
from datetime import date

import akshare as ak
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.calendar_repository import calendar_repository
from src.services.ak_trace import trace_akshare

logger = logging.getLogger(__name__)


@trace_akshare("tool_trade_date_hist_sina")
def _fetch_all() -> pd.DataFrame:
    return ak.tool_trade_date_hist_sina()


class CalendarService:
    def __init__(self):
        self._dates: list[date] = []

    @property
    def dates(self) -> list[date]:
        return self._dates

    async def load(self, session: AsyncSession) -> None:
        self._dates = await calendar_repository.get_all_dates(session)
        if self._dates:
            logger.info("calendar loaded %d trading days from DB", len(self._dates))
        else:
            logger.info("calendar empty, fetching from akshare")
            await self._sync(session)
        logger.info("calendar ready: %s ~ %s (%d days)",
                     self._dates[0], self._dates[-1], len(self._dates))

    async def ensure_fresh(self, session: AsyncSession) -> None:
        today = date.today()
        if self._dates and self._dates[-1] >= today:
            return
        logger.info("calendar stale (last: %s), refreshing", self._dates[-1] if self._dates else "N/A")
        await self._sync(session)

    async def _sync(self, session: AsyncSession) -> None:
        logger.info("fetching trading calendar from akshare")
        df = await _fetch_all()
        logger.info("akshare returned %d trading days, columns=%s", len(df), list(df.columns))
        rows = [(d,) for d in df["trade_date"]]
        logger.info("calendar upsert starting (%d rows)...", len(rows))
        if rows:
            logger.info("first 3 rows: %s, last row: %s", rows[:3], rows[-1])
        await calendar_repository.upsert_many(session, rows)
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

    def is_trading_day(self, d: date) -> bool:
        idx = bisect.bisect_left(self._dates, d)
        return idx < len(self._dates) and self._dates[idx] == d

    def get_range(self, start: date, end: date) -> list[date]:
        lo = bisect.bisect_left(self._dates, start)
        hi = bisect.bisect_right(self._dates, end)
        return self._dates[lo:hi]


calendar_service = CalendarService()
