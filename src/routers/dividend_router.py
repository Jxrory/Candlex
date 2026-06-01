import logging
from datetime import date

import asyncpg
from fastapi import APIRouter, Depends, Query, Path

from src.database import get_conn
from src.schemas.schemas import DividendRecord
from src.services.dividend_service import dividend_service

logger = logging.getLogger(__name__)
router = APIRouter(tags=["dividend"])


@router.get("/dividend/{symbol}", response_model=list[DividendRecord])
async def dividend(
    symbol: str = Path(pattern=r"^(SH|SZ|BJ)\.[0-9]{6}$"),
    start: date | None = Query(None),
    end: date | None = Query(None),
    refresh: bool = Query(False),
    conn: asyncpg.Connection = Depends(get_conn),
):
    logger.info("GET /dividend/%s refresh=%s start=%s end=%s", symbol, refresh, start, end)
    if refresh:
        await dividend_service.sync_symbol(conn, symbol)
    records = await dividend_service.get_events(conn, symbol, start, end)

    if not records and not refresh:
        logger.info("GET /dividend/%s no cached data, auto-syncing", symbol)
        count = await dividend_service.sync_symbol(conn, symbol)
        logger.info("GET /dividend/%s auto-sync completed: %d records", symbol, count)
        records = await dividend_service.get_events(conn, symbol, start, end)

    logger.info("GET /dividend/%s returned %d records", symbol, len(records))
    return records
