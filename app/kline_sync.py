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
