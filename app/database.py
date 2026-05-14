import asyncio
import logging

import asyncpg
from app.config import settings

logger = logging.getLogger(__name__)

pool: asyncpg.Pool | None = None
_lock = asyncio.Lock()


async def get_pool() -> asyncpg.Pool:
    global pool
    if pool is None:
        async with _lock:
            if pool is None:
                logger.info("creating connection pool to %s", settings.db_dsn)
                pool = await asyncpg.create_pool(
                    dsn=settings.db_dsn,
                    min_size=settings.db_min_connections,
                    max_size=settings.db_max_connections,
                    timeout=10,
                    command_timeout=30,
                )
                logger.info("connection pool created")
    return pool


async def close_pool() -> None:
    global pool
    if pool:
        logger.info("closing connection pool")
        await pool.close()
        pool = None
