import logging
from datetime import date

import asyncpg

logger = logging.getLogger(__name__)


class CalendarRepository:
    async def get_all_dates(self, conn: asyncpg.Connection) -> list[date]:
        rows = await conn.fetch(
            "SELECT trade_date FROM trade_calendar ORDER BY trade_date"
        )
        return [r["trade_date"] for r in rows]

    async def upsert_many(
        self, conn: asyncpg.Connection, rows: list[tuple]
    ) -> None:
        if not rows:
            return
        await conn.executemany(
            "INSERT INTO trade_calendar (trade_date, updated_at) VALUES ($1, NOW()) ON CONFLICT (trade_date) DO UPDATE SET updated_at=NOW()",
            rows,
            timeout=120,
        )


calendar_repository = CalendarRepository()
