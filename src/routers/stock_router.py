import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.schemas.schemas import StockInfoRecord
from src.services.stock_list_service import stock_list_service

logger = logging.getLogger(__name__)
router = APIRouter(tags=["stocks"])


@router.get("/stocks", response_model=list[StockInfoRecord])
async def stocks(
    market: str | None = Query(None),
    refresh: bool = Query(False),
    session: AsyncSession = Depends(get_db),
):
    logger.info("GET /stocks market=%s refresh=%s", market, refresh)
    if refresh:
        market_to_sync = market or "ZH_A"
        count = await stock_list_service.sync(session, market_to_sync)
        logger.info("GET /stocks sync completed: %d records for %s", count, market_to_sync)
    records = await stock_list_service.get_stocks(session, market)
    logger.info("GET /stocks returned %d records", len(records))
    return records
