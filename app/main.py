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


# sync_all_dividends: scheduled dividend sync for all symbols (removed, not in use)

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


# sync_kline: scheduled kline backfill for pending stocks (removed, not in use)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("CandleX starting up")
    await calendar_service.load()
    await get_pool()
    global _writer_task
    _writer_task = asyncio.create_task(_log_writer())

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
