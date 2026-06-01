import logging
from datetime import date, timedelta

import asyncpg

from src.repositories.stock_list_repository import stock_list_repository
from src.services.kline_service import get_kline

logger = logging.getLogger(__name__)

Y2000 = date(2000, 1, 1)


class KlineSyncService:

    async def sync_one(self, pool: asyncpg.Pool, source: str | None = None) -> int:
        async with pool.acquire() as conn:
            symbol = await stock_list_repository.get_next_pending(conn)
        if not symbol:
            logger.info("no stocks pending kline sync")
            return 0

        yesterday = date.today() - timedelta(days=1)
        try:
            records = await get_kline(symbol, Y2000, yesterday, source=source)
            async with pool.acquire() as conn:
                await stock_list_repository.mark_synced(conn, symbol)
            logger.info("synced kline for %s (%d rows)", symbol, len(records))
            return 1
        except Exception as e:
            logger.error("kline sync failed for %s: %s", symbol, e)
            return 0


kline_sync_service = KlineSyncService()
