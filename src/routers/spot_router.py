import logging

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, Path

from src.database import get_conn
from src.services.spot_service import spot_service

logger = logging.getLogger(__name__)
router = APIRouter(tags=["spot"])


@router.get("/quote/spot/real", response_model=list[dict])
async def spot_real(
    codes: str | None = Query(None, description="comma-separated codes, e.g. 600519,000001"),
):
    logger.info("GET /quote/spot/real codes=%s", codes)
    records = await spot_service.fetch_real()
    if codes:
        code_set = set(c.strip() for c in codes.split(","))
        records = [r for r in records if str(r.get("代码", "")) in code_set]
    logger.info("GET /quote/spot/real returned %d records", len(records))
    return records


@router.get("/quote/spot/real/{symbol}")
async def spot_real_symbol(
    symbol: str = Path(pattern=r"^(SH|SZ|BJ)\.[0-9]{6}$"),
):
    logger.info("GET /quote/spot/real/%s", symbol)
    records = await spot_service.fetch_real(symbol)
    logger.info("GET /quote/spot/real/%s returned %d records", symbol, len(records))
    return records


@router.get("/quote/spot", response_model=list[dict])
async def spot(conn: asyncpg.Connection = Depends(get_conn)):
    logger.info("GET /quote/spot")
    records = await spot_service.get_latest(conn)
    logger.info("GET /quote/spot returned %d records", len(records))
    return records


@router.get("/quote/spot/{symbol}")
async def spot_symbol(
    symbol: str = Path(pattern=r"^(SH|SZ|BJ)\.[0-9]{6}$"),
    conn: asyncpg.Connection = Depends(get_conn),
):
    logger.info("GET /quote/spot/%s", symbol)
    records = await spot_service.get_latest(conn, symbol)
    logger.info("GET /quote/spot/%s returned %d records", symbol, len(records))
    return records


@router.get("/quote/sync", response_model=dict)
async def spot_sync(conn: asyncpg.Connection = Depends(get_conn)):
    logger.info("GET /quote/spot/sync")
    try:
        count = await spot_service.sync_all(conn)
        logger.info("GET /quote/spot/sync completed: %d records", count)
        return {"synced": count}
    except Exception as e:
        logger.error("GET /quote/spot/sync failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
