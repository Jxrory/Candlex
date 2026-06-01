import logging
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.config import settings

logger = logging.getLogger(__name__)

engine: AsyncEngine | None = None
async_session_maker: async_sessionmaker[AsyncSession] | None = None


async def get_engine() -> AsyncEngine:
    global engine, async_session_maker
    if engine is None:
        logger.info("creating sqlalchemy async engine for %s", settings.db_dsn)
        engine = create_async_engine(
            settings.db_dsn,
            echo=settings.db_echo,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_recycle=3600,
        )
        async_session_maker = async_sessionmaker(engine, expire_on_commit=False)
        logger.info("async engine created")
    return engine


async def get_db() -> AsyncGenerator[AsyncSession]:
    await get_engine()
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def close_engine() -> None:
    global engine
    if engine:
        logger.info("disposing engine")
        await engine.dispose()
        engine = None
        logger.info("engine disposed")
