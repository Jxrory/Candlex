import logging
from datetime import date

import asyncpg
from fastapi import APIRouter, Depends, Query, Path

from src.database import get_conn
from src.services.financial_service import get_financial_data, query_financial

logger = logging.getLogger(__name__)
router = APIRouter(tags=["financial"])


@router.get("/v2/financial/query")
async def financial_v2_query(
    report_date_start: date | None = Query(None, alias="report_date_start"),
    report_date_end: date | None = Query(None, alias="report_date_end"),
    roe_min: float | None = Query(None, alias="roe_min"),
    roe_max: float | None = Query(None, alias="roe_max"),
    debt_ratio_min: float | None = Query(None, alias="debt_ratio_min"),
    debt_ratio_max: float | None = Query(None, alias="debt_ratio_max"),
    eps_min: float | None = Query(None, alias="eps_min"),
    eps_max: float | None = Query(None, alias="eps_max"),
    revenue_growth_min: float | None = Query(None, alias="revenue_growth_min"),
    revenue_growth_max: float | None = Query(None, alias="revenue_growth_max"),
    net_profit_growth_min: float | None = Query(None, alias="net_profit_growth_min"),
    net_profit_growth_max: float | None = Query(None, alias="net_profit_growth_max"),
    gross_margin_min: float | None = Query(None, alias="gross_margin_min"),
    gross_margin_max: float | None = Query(None, alias="gross_margin_max"),
    current_ratio_min: float | None = Query(None, alias="current_ratio_min"),
    current_ratio_max: float | None = Query(None, alias="current_ratio_max"),
    roa_min: float | None = Query(None, alias="roa_min"),
    roa_max: float | None = Query(None, alias="roa_max"),
    conn: asyncpg.Connection = Depends(get_conn),
):
    logger.info(
        "GET /v2/financial/query report_date_start=%s report_date_end=%s roe_min=%s debt_ratio_min=%s",
        report_date_start, report_date_end, roe_min, debt_ratio_min,
    )
    filters: dict[str, tuple[float | None, float | None]] = {}
    explicit_filters = [
        ("roe", roe_min, roe_max),
        ("debt_ratio", debt_ratio_min, debt_ratio_max),
        ("eps", eps_min, eps_max),
        ("revenue_growth", revenue_growth_min, revenue_growth_max),
        ("net_profit_growth", net_profit_growth_min, net_profit_growth_max),
        ("gross_margin", gross_margin_min, gross_margin_max),
        ("current_ratio", current_ratio_min, current_ratio_max),
        ("roa", roa_min, roa_max),
    ]
    for name, min_val, max_val in explicit_filters:
        if min_val is not None or max_val is not None:
            filters[name] = (min_val, max_val)
    records = await query_financial(conn, filters, report_date_start, report_date_end)
    symbol_count = len(records)
    period_count = sum(len(v) for v in records.values())
    logger.info("GET /v2/financial/query returned %d symbols (%d periods)", symbol_count, period_count)
    return records


@router.get("/v2/financial/{symbol}")
async def financial_v2(
    symbol: str = Path(pattern=r"^(SH|SZ|BJ)\.[0-9]{6}$"),
    start: date | None = Query(None),
    end: date | None = Query(None),
    conn: asyncpg.Connection = Depends(get_conn),
):
    logger.info("GET /v2/financial/%s start=%s end=%s", symbol, start, end)
    records = await get_financial_data(conn, symbol, start, end)
    logger.info("GET /v2/financial/%s returned %d records", symbol, len(records))
    return records
