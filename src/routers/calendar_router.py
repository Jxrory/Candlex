import logging
from datetime import date

from fastapi import APIRouter, Query

from src.services.calendar_service import calendar_service

logger = logging.getLogger(__name__)
router = APIRouter(tags=["calendar"])


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
