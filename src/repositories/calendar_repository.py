import logging
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.calendar import TradeCalendar

logger = logging.getLogger(__name__)


class CalendarRepository:
    async def get_all_dates(self, session: AsyncSession) -> list[date]:
        stmt = select(TradeCalendar.trade_date).order_by(TradeCalendar.trade_date)
        result = await session.execute(stmt)
        return [r[0] for r in result]

    async def upsert_many(
        self, session: AsyncSession, rows: list[tuple]
    ) -> None:
        if not rows:
            return
        for row in rows:
            await session.merge(TradeCalendar(trade_date=row[0]))


calendar_repository = CalendarRepository()
