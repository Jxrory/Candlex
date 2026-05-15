import logging
from datetime import date, timedelta
from fastapi import APIRouter, Query, Path

from app.calendar import calendar_service
from app.dividend import dividend_service
from app.database import get_pool
from app.schemas import KlineRecord, DividendRecord
from app.service import get_kline

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/calendar", response_model=list[date])
async def calendar(
    start: date | None = Query(None),
    end: date | None = Query(None),
):
    today = date.today()
    if end is None:
        end = date(today.year, 12, 31)
    if start is None:
        start = date(today.year, 1, 1)
    return calendar_service.get_range(start, end)


@router.get("/kline/{symbol}", response_model=list[KlineRecord])
async def kline(
    symbol: str = Path(pattern=r"^(SH|SZ|BJ)\.[0-9]{6}$"),
    start: date | None = Query(None),
    end: date | None = Query(None),
    adjust: str | None = Query(None, pattern="^(qfq|hfq)$"),
):
    today = date.today()
    if end is None:
        end = today
    if start is None:
        start = today - timedelta(days=365)

    logger.info("GET /kline/%s start=%s end=%s adjust=%s", symbol, start, end, adjust)
    records = await get_kline(symbol, start, end, adjust)
    logger.info("GET /kline/%s returned %d records", symbol, len(records))
    return records


@router.get("/dividend/{symbol}", response_model=list[DividendRecord])
async def dividend(
    symbol: str = Path(pattern=r"^(SH|SZ|BJ)\.[0-9]{6}$"),
    start: date | None = Query(None),
    end: date | None = Query(None),
):
    logger.info("GET /dividend/%s start=%s end=%s", symbol, start, end)
    pool = await get_pool()
    await dividend_service.ensure_fresh(pool, symbol)
    records = await dividend_service.get_events(pool, symbol, start, end)
    logger.info("GET /dividend/%s returned %d records", symbol, len(records))
    return records
