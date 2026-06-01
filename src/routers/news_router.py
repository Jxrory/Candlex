import logging
from datetime import datetime

import asyncpg
from fastapi import APIRouter, Depends, Query, Path

from src.database import get_conn
from src.schemas.schemas import NewsRecord
from src.services.news_service import news_service

logger = logging.getLogger(__name__)
router = APIRouter(tags=["news"])


@router.get("/news/{symbol}", response_model=list[NewsRecord])
async def news(
    symbol: str = Path(pattern=r"^(SH|SZ|BJ)\.[0-9]{6}$"),
    start: datetime | None = Query(None),
    end: datetime | None = Query(None),
    refresh: bool = Query(False),
    conn: asyncpg.Connection = Depends(get_conn),
):
    logger.info("GET /news/%s refresh=%s start=%s end=%s", symbol, refresh, start, end)
    if refresh:
        count = await news_service.sync_symbol(conn, symbol)
        logger.info("GET /news/%s sync completed: %d records", symbol, count)
    records = await news_service.get_news(conn, symbol, start, end)

    if not records and not refresh:
        logger.info("GET /news/%s no cached data, auto-syncing", symbol)
        count = await news_service.sync_symbol(conn, symbol)
        logger.info("GET /news/%s auto-sync completed: %d records", symbol, count)
        records = await news_service.get_news(conn, symbol, start, end)

    logger.info("GET /news/%s returned %d records", symbol, len(records))
    return records
