import logging
from datetime import date, timedelta
from fastapi import APIRouter, Query, Path

from app.calendar import calendar_service
from app.dividend import dividend_service
from app.database import get_pool
from app.schemas import (
    KlineRecord, DividendRecord, StockInfoRecord,
    FinancialIndicatorRecord, BalanceSheetRecord, ProfitSheetRecord,
    CashFlowSheetRecord,
)
from app.service import get_kline
from app.stock_list import stock_list_service
from app.financial_indicator import financial_indicator_service
from app.balance_sheet import balance_sheet_service
from app.profit_sheet import profit_sheet_service
from app.cash_flow_sheet import cash_flow_sheet_service

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
    refresh: bool = Query(False),
):
    logger.info("GET /dividend/%s refresh=%s start=%s end=%s", symbol, refresh, start, end)
    pool = await get_pool()
    if refresh:
        await dividend_service.sync_symbol(pool, symbol)
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


@router.get("/indicator/{symbol}", response_model=list[FinancialIndicatorRecord])
async def indicator(
    symbol: str = Path(pattern=r"^(SH|SZ|BJ)\.[0-9]{6}$"),
    start: date | None = Query(None),
    end: date | None = Query(None),
    refresh: bool = Query(False),
):
    logger.info("GET /indicator/%s refresh=%s start=%s end=%s", symbol, refresh, start, end)
    pool = await get_pool()
    if refresh:
        count = await financial_indicator_service.sync_symbol(pool, symbol)
        logger.info("GET /indicator/%s sync completed: %d records", symbol, count)
    records = await financial_indicator_service.get_indicators(pool, symbol, start, end)
    logger.info("GET /indicator/%s returned %d records", symbol, len(records))
    return records


@router.get("/balance/{symbol}", response_model=list[BalanceSheetRecord])
async def balance(
    symbol: str = Path(pattern=r"^(SH|SZ|BJ)\.[0-9]{6}$"),
    start: date | None = Query(None),
    end: date | None = Query(None),
    refresh: bool = Query(False),
):
    logger.info("GET /balance/%s refresh=%s start=%s end=%s", symbol, refresh, start, end)
    pool = await get_pool()
    if refresh:
        count = await balance_sheet_service.sync_symbol(pool, symbol)
        logger.info("GET /balance/%s sync completed: %d records", symbol, count)
    records = await balance_sheet_service.get_balance_sheets(pool, symbol, start, end)
    logger.info("GET /balance/%s returned %d records", symbol, len(records))
    return records


@router.get("/profit/{symbol}", response_model=list[ProfitSheetRecord])
async def profit(
    symbol: str = Path(pattern=r"^(SH|SZ|BJ)\.[0-9]{6}$"),
    start: date | None = Query(None),
    end: date | None = Query(None),
    refresh: bool = Query(False),
):
    logger.info("GET /profit/%s refresh=%s start=%s end=%s", symbol, refresh, start, end)
    pool = await get_pool()
    if refresh:
        count = await profit_sheet_service.sync_symbol(pool, symbol)
        logger.info("GET /profit/%s sync completed: %d records", symbol, count)
    records = await profit_sheet_service.get_profit_sheets(pool, symbol, start, end)
    logger.info("GET /profit/%s returned %d records", symbol, len(records))
    return records


@router.get("/cash-flow/{symbol}", response_model=list[CashFlowSheetRecord])
async def cash_flow(
    symbol: str = Path(pattern=r"^(SH|SZ|BJ)\.[0-9]{6}$"),
    start: date | None = Query(None),
    end: date | None = Query(None),
    refresh: bool = Query(False),
):
    logger.info("GET /cash-flow/%s refresh=%s start=%s end=%s", symbol, refresh, start, end)
    pool = await get_pool()
    if refresh:
        count = await cash_flow_sheet_service.sync_symbol(pool, symbol)
        logger.info("GET /cash-flow/%s sync completed: %d records", symbol, count)
    records = await cash_flow_sheet_service.get_cash_flow_sheets(pool, symbol, start, end)
    logger.info("GET /cash-flow/%s returned %d records", symbol, len(records))
    return records
