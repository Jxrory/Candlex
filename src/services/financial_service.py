import logging
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.financial import (
    FinancialPerShare,
    FinancialBalanceSheet,
    FinancialIncomeSheet,
    FinancialCashFlow,
    FinancialRatio,
    FinancialHoldings,
)
from src.models.financial_mapping import TABLE_COLUMNS, ENGLISH_TO_TABLE
from src.repositories.financial_repository import financial_repository

logger = logging.getLogger(__name__)

FINANCIAL_TABLES = sorted(TABLE_COLUMNS.keys())

_FINANCIAL_MODEL_MAP = {
    "financial_per_share": FinancialPerShare,
    "financial_balance_sheet": FinancialBalanceSheet,
    "financial_income_sheet": FinancialIncomeSheet,
    "financial_cash_flow": FinancialCashFlow,
    "financial_ratio": FinancialRatio,
    "financial_holdings": FinancialHoldings,
}

_QUARTER_END = {1: (3, 31), 2: (6, 30), 3: (9, 30), 4: (12, 31)}


def _last_n_quarter_dates(n: int = 4) -> list[date]:
    today = date.today()
    current_q = (today.month - 1) // 3 + 1
    if current_q == 1:
        recent_q, recent_year = 4, today.year - 1
    else:
        recent_q, recent_year = current_q - 1, today.year
    result: list[date] = []
    for i in range(n):
        q = recent_q - i
        y = recent_year
        while q <= 0:
            q += 4
            y -= 1
        m, d = _QUARTER_END[q]
        result.append(date(y, m, d))
    return result


def _default_report_date_range() -> tuple[date, date]:
    dates = _last_n_quarter_dates(4)
    return (dates[-1], dates[0])


async def get_financial_data(
    session: AsyncSession,
    symbol: str,
    start: date | None = None,
    end: date | None = None,
) -> list[dict]:
    return await financial_repository.get_symbol_data(session, symbol, start, end)


async def query_financial(
    session: AsyncSession,
    filters: dict[str, tuple[float | None, float | None]],
    report_date_start: date | None = None,
    report_date_end: date | None = None,
) -> dict[str, list[dict]]:
    if not filters:
        return {}

    table_filters: dict[str, dict[str, tuple[float | None, float | None]]] = {}
    for col_name, (min_val, max_val) in filters.items():
        table_name = ENGLISH_TO_TABLE.get(col_name)
        if table_name is None:
            logger.warning("unknown column for filtering: %s", col_name)
            continue
        table_filters.setdefault(table_name, {})[col_name] = (min_val, max_val)

    if not table_filters:
        return {}

    primary_table = next(iter(table_filters))
    primary_filters = table_filters[primary_table]
    primary_model = _FINANCIAL_MODEL_MAP[primary_table]

    if report_date_start is None and report_date_end is None:
        report_date_start, report_date_end = _default_report_date_range()

    where_clauses = []
    if report_date_start is not None:
        where_clauses.append(primary_model.report_date >= report_date_start)
    if report_date_end is not None:
        where_clauses.append(primary_model.report_date <= report_date_end)

    for col_name, (min_val, max_val) in primary_filters.items():
        model_col = getattr(primary_model, col_name, None)
        if model_col is None:
            logger.warning("unknown model column: %s.%s", primary_table, col_name)
            continue
        if min_val is not None:
            where_clauses.append(model_col >= min_val)
        if max_val is not None:
            where_clauses.append(model_col <= max_val)

    if not where_clauses:
        return {}

    matching = await financial_repository.query_filtered(
        session, primary_table, where_clauses, []
    )

    if not matching:
        return {}

    symbol_dates: dict[str, set[date]] = {}
    for r in matching:
        sym: str = r["symbol"]
        rd: date = r["report_date"]
        symbol_dates.setdefault(sym, set()).add(rd)

    async def _fetch_symbol_all_dates(sym: str, rds: set[date]) -> tuple[str, dict[date, dict]]:
        merged_by_date: dict[date, dict] = {}
        for tbl in FINANCIAL_TABLES:
            rows = await financial_repository.fetch_symbol_rows(session, tbl, sym, list(rds))
            for row in rows:
                rd = row["report_date"]
                if rd not in merged_by_date:
                    merged_by_date[rd] = {"symbol": sym, "report_date": rd}
                for k, v in row.items():
                    if k not in ("symbol", "report_date", "source", "updated_at"):
                        merged_by_date[rd][k] = v
        return sym, merged_by_date

    symbol_results = []
    for sym, rds in symbol_dates.items():
        symbol_results.append(await _fetch_symbol_all_dates(sym, rds))

    result: dict[str, list[dict]] = {}
    for sym, merged_by_date in symbol_results:
        result[sym] = [merged_by_date[rd] for rd in sorted(merged_by_date.keys())]

    return result


__all__ = ["get_financial_data", "query_financial"]
