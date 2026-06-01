import logging
from datetime import date

import asyncpg

logger = logging.getLogger(__name__)


class KlineRepository:
    async def get_cached(
        self, conn: asyncpg.Connection, symbol: str, start: date, end: date
    ) -> list[asyncpg.Record]:
        return await conn.fetch(
            """SELECT date, open, high, low, close, volume, amount
               FROM kline_data
               WHERE symbol = $1 AND date BETWEEN $2 AND $3
               ORDER BY date""",
            symbol, start, end,
        )

    async def upsert_many(
        self, conn: asyncpg.Connection, rows: list[tuple]
    ) -> None:
        if not rows:
            return
        await conn.executemany(
            """INSERT INTO kline_data
               (symbol, date, open, high, low, close, volume, amount, source)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
               ON CONFLICT (symbol, date)
               DO UPDATE SET
                   open=EXCLUDED.open, high=EXCLUDED.high,
                   low=EXCLUDED.low, close=EXCLUDED.close,
                   volume=EXCLUDED.volume, amount=EXCLUDED.amount,
                   source=EXCLUDED.source""",
            rows,
        )


kline_repository = KlineRepository()
