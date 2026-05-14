from datetime import date, timedelta
from fastapi import APIRouter, Query

from app.schemas import KlineRecord
from app.service import get_kline

router = APIRouter()


@router.get("/kline/{symbol}", response_model=list[KlineRecord])
async def kline(
    symbol: str,
    start: date | None = Query(None),
    end: date | None = Query(None),
    adjust: str | None = Query(None, pattern="^(qfq|hfq)$"),
):
    today = date.today()
    if end is None:
        end = today
    if start is None:
        start = today - timedelta(days=365)

    return await get_kline(symbol, start, end, adjust)
