import asyncpg
from app.config import settings


pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global pool
    if pool is None:
        pool = await asyncpg.create_pool(
            dsn=settings.db_dsn,
            min_size=settings.db_min_connections,
            max_size=settings.db_max_connections,
        )
    return pool


async def close_pool() -> None:
    global pool
    if pool:
        await pool.close()
        pool = None
