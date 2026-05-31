import logging
from datetime import date, timedelta

import asyncpg

from app.service import get_kline

logger = logging.getLogger(__name__)

Y2000 = date(2000, 1, 1)


class KlineSyncService:

    async def sync_one(self, pool: asyncpg.Pool, source: str | None = None) -> int:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT symbol FROM stock_info "
                "WHERE list_status IS NULL "
                "LIMIT 1"
            )
        if not row:
            logger.info("no stocks pending kline sync")
            return 0

        symbol = row["symbol"]
        yesterday = date.today() - timedelta(days=1)
        try:
            records = await get_kline(symbol, Y2000, yesterday, source=source)
            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE stock_info SET list_status = 'SYNCED', list_date = NOW() WHERE symbol = $1",
                    symbol,
                )
            logger.info("synced kline for %s (%d rows)", symbol, len(records))
            return 1
        except Exception as e:
            logger.error("kline sync failed for %s: %s", symbol, e)
            return 0


kline_sync_service = KlineSyncService()
