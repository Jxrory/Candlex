import logging

import asyncpg
from fastapi import APIRouter, Depends, Query

from src.database import get_conn
from src.schemas.schemas import StockInfoRecord
from src.services.stock_list_service import stock_list_service

logger = logging.getLogger(__name__)
router = APIRouter(tags=["stocks"])


@router.get("/stocks", response_model=list[StockInfoRecord])
async def stocks(
    market: str | None = Query(None),
    refresh: bool = Query(False),
    conn: asyncpg.Connection = Depends(get_conn),
):
    logger.info("GET /stocks market=%s refresh=%s", market, refresh)
    if refresh:
        market_to_sync = market or "ZH_A"
        count = await stock_list_service.sync(conn, market_to_sync)
        logger.info("GET /stocks sync completed: %d records for %s", count, market_to_sync)
    records = await stock_list_service.get_stocks(conn, market)
    logger.info("GET /stocks returned %d records", len(records))
    return records
