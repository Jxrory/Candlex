import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI

from app.calendar import calendar_service
from app.dividend import dividend_service
from app.stock_list import stock_list_service
from app.spot import spot_service
from app.database import get_pool, close_pool
from app.ak_trace import _log_writer
from app.router import router
from app.config import settings

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()
_writer_task: asyncio.Task | None = None


async def sync_all_dividends():
    logger.info("scheduled task: sync dividends for all symbols")
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT DISTINCT symbol FROM kline_data ORDER BY symbol"
        )
    symbols = [r["symbol"] for r in rows]
    if settings.dividend_sync_symbols:
        symbols = [s for s in symbols if s in settings.dividend_sync_symbols]
    for symbol in symbols:
        try:
            count = await dividend_service.sync_symbol(pool, symbol)
            if count:
                logger.info("synced %d events for %s", count, symbol)
        except Exception as e:
            logger.error("dividend sync failed for %s: %s", symbol, e)
    logger.info("scheduled task: dividend sync complete")


async def sync_stock_list():
    logger.info("scheduled task: sync stock list")
    pool = await get_pool()
    try:
        count = await stock_list_service.sync(pool, "ZH_A")
        logger.info("scheduled task: synced %d stock records", count)
    except Exception as e:
        logger.error("scheduled task: stock list sync failed: %s", e)


async def sync_spot_snapshot():
    logger.info("scheduled task: sync spot snapshot")
    pool = await get_pool()
    try:
        count = await spot_service.sync_all(pool)
        logger.info("scheduled task: synced %d spot records", count)
    except Exception as e:
        logger.error("scheduled task: spot sync failed: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("CandleX starting up")
    await calendar_service.load()
    await get_pool()
    global _writer_task
    _writer_task = asyncio.create_task(_log_writer())

    # hour, minute = settings.dividend_sync_time.split(":")
    # scheduler.add_job(
    #     sync_all_dividends,
    #     trigger="cron",
    #     hour=int(hour),
    #     minute=int(minute),
    #     id="sync_dividends",
    #     replace_existing=True,
    # )
    # scheduler.start()
    # logger.info("scheduler started, dividend sync at %s", settings.dividend_sync_time)

    scheduler.add_job(
        sync_stock_list,
        trigger="cron",
        day=15,
        hour=8,
        minute=30,
        id="sync_stock_list",
        replace_existing=True,
    )
    scheduler.add_job(
        sync_spot_snapshot,
        trigger="cron",
        hour=17, minute=0,
        id="sync_spot_snapshot",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("scheduler started, stock list sync at 08:30 on day 15")

    yield
    if _writer_task is not None:
        _writer_task.cancel()
    scheduler.shutdown()
    await close_pool()
    logger.info("CandleX shut down")


app = FastAPI(title="CandleX", lifespan=lifespan)
app.include_router(router)
