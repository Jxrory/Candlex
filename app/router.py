import logging
from datetime import date, datetime, timedelta
from fastapi import APIRouter, HTTPException, Query, Path

from app.calendar import calendar_service
from app.dividend import dividend_service
from app.database import get_pool
from app.schemas import (
    KlineRecord, DividendRecord, StockInfoRecord, NewsRecord,
)
from app.service import get_kline
from app.stock_list import stock_list_service
from app.indicators_service import get_indicators, parse_specs
from app.financial_v2 import get_financial_data, query_financial
from app.news import news_service
from app.spot import spot_service

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


@router.get("/dividend/{symbol}", response_model=list[DividendRecord])
async def dividend(
    symbol: str = Path(pattern=r"^(SH|SZ|BJ)\.[0-9]{6}$"),
    start: date | None = Query(None),
    end: date | None = Query(None),
    refresh: bool = Query(False),
):
    logger.info("GET /dividend/%s refresh=%s start=%s end=%s", symbol, refresh, start, end)
    pool = await get_pool()
    if refresh:
        await dividend_service.sync_symbol(pool, symbol)
    records = await dividend_service.get_events(pool, symbol, start, end)

    if not records and not refresh:
        logger.info("GET /dividend/%s no cached data, auto-syncing", symbol)
        count = await dividend_service.sync_symbol(pool, symbol)
        logger.info("GET /dividend/%s auto-sync completed: %d records", symbol, count)
        records = await dividend_service.get_events(pool, symbol, start, end)

    logger.info("GET /dividend/%s returned %d records", symbol, len(records))
    return records


@router.get("/stocks", response_model=list[StockInfoRecord])
async def stocks(
    market: str | None = Query(None),
    refresh: bool = Query(False),
):
    logger.info("GET /stocks market=%s refresh=%s", market, refresh)
    pool = await get_pool()
    if refresh:
        market_to_sync = market or "ZH_A"
        count = await stock_list_service.sync(pool, market_to_sync)
        logger.info("GET /stocks sync completed: %d records for %s", count, market_to_sync)
    records = await stock_list_service.get_stocks(pool, market)
    logger.info("GET /stocks returned %d records", len(records))
    return records



@router.get("/news/{symbol}", response_model=list[NewsRecord])
async def news(
    symbol: str = Path(pattern=r"^(SH|SZ|BJ)\.[0-9]{6}$"),
    start: datetime | None = Query(None),
    end: datetime | None = Query(None),
    refresh: bool = Query(False),
):
    logger.info("GET /news/%s refresh=%s start=%s end=%s", symbol, refresh, start, end)
    pool = await get_pool()
    if refresh:
        count = await news_service.sync_symbol(pool, symbol)
        logger.info("GET /news/%s sync completed: %d records", symbol, count)
    records = await news_service.get_news(pool, symbol, start, end)

    if not records and not refresh:
        logger.info("GET /news/%s no cached data, auto-syncing", symbol)
        count = await news_service.sync_symbol(pool, symbol)
        logger.info("GET /news/%s auto-sync completed: %d records", symbol, count)
        records = await news_service.get_news(pool, symbol, start, end)

    logger.info("GET /news/%s returned %d records", symbol, len(records))
    return records


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
async def spot():
    logger.info("GET /quote/spot")
    pool = await get_pool()
    records = await spot_service.get_latest(pool)
    logger.info("GET /quote/spot returned %d records", len(records))
    return records


@router.get("/quote/spot/{symbol}")
async def spot_symbol(
    symbol: str = Path(pattern=r"^(SH|SZ|BJ)\.[0-9]{6}$"),
):
    logger.info("GET /quote/spot/%s", symbol)
    pool = await get_pool()
    records = await spot_service.get_latest(pool, symbol)
    logger.info("GET /quote/spot/%s returned %d records", symbol, len(records))
    return records


@router.get("/quote/sync", response_model=dict)
async def spot_sync():
    logger.info("GET /quote/spot/sync")
    pool = await get_pool()
    try:
        count = await spot_service.sync_all(pool)
        logger.info("GET /quote/spot/sync completed: %d records", count)
        return {"synced": count}
    except Exception as e:
        logger.error("GET /quote/spot/sync failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


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
):
    logger.info(
        "GET /v2/financial/query report_date_start=%s report_date_end=%s roe_min=%s debt_ratio_min=%s",
        report_date_start, report_date_end, roe_min, debt_ratio_min,
    )
    pool = await get_pool()
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
    records = await query_financial(pool, filters, report_date_start, report_date_end)
    symbol_count = len(records)
    period_count = sum(len(v) for v in records.values())
    logger.info("GET /v2/financial/query returned %d symbols (%d periods)", symbol_count, period_count)
    # logger.debug("GET /v2/financial/query returned %s", records)
    return records


@router.get("/v2/financial/{symbol}")
async def financial_v2(
    symbol: str = Path(pattern=r"^(SH|SZ|BJ)\.[0-9]{6}$"),
    start: date | None = Query(None),
    end: date | None = Query(None),
):
    logger.info("GET /v2/financial/%s start=%s end=%s", symbol, start, end)
    pool = await get_pool()
    records = await get_financial_data(pool, symbol, start, end)
    logger.info("GET /v2/financial/%s returned %d records", symbol, len(records))
    return records
