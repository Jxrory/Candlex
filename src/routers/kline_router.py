import logging
from datetime import date, timedelta

from fastapi import APIRouter, HTTPException, Query, Path

from src.schemas.schemas import KlineRecord
from src.services.kline_service import get_kline
from src.services.indicators_service import get_indicators, parse_specs

logger = logging.getLogger(__name__)
router = APIRouter(tags=["kline"])


@router.get("/kline/{symbol}", response_model=list[KlineRecord])
async def kline(
    symbol: str = Path(pattern=r"^(SH|SZ|BJ)\.[0-9]{6}$"),
    start: date | None = Query(None),
    end: date | None = Query(None),
    adjust: str | None = Query(None, pattern="^(qfq|hfq)$"),
    source: str | None = Query(None),
):
    today = date.today()
    if end is None:
        end = today
    if start is None:
        start = today - timedelta(days=365)

    logger.info("GET /kline/%s start=%s end=%s adjust=%s source=%s", symbol, start, end, adjust, source)
    records = await get_kline(symbol, start, end, adjust, source=source)
    logger.info("GET /kline/%s returned %d records", symbol, len(records))
    return records


@router.get("/indicators/{symbol}")
async def indicators(
    symbol: str = Path(pattern=r"^(SH|SZ|BJ)\.[0-9]{6}$"),
    start: date | None = Query(None),
    end: date | None = Query(None),
    adjust: str | None = Query(None, pattern="^(qfq|hfq)$"),
    i: list[str] = Query(default_factory=list),
):
    today = date.today()
    if end is None:
        end = today
    if start is None:
        start = today - timedelta(days=365)

    logger.info("GET /indicators/%s start=%s end=%s adjust=%s i=%s", symbol, start, end, adjust, i)
    try:
        specs = parse_specs(i)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    result = await get_indicators(symbol, start, end, adjust, specs)
    logger.info("GET /indicators/%s returned %d records", symbol, len(result))
    return result
