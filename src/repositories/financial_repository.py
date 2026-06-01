import logging
from datetime import date

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.financial import (
    FinancialPerShare,
    FinancialBalanceSheet,
    FinancialIncomeSheet,
    FinancialCashFlow,
    FinancialRatio,
    FinancialHoldings,
)
from src.models.financial_mapping import TABLE_COLUMNS

logger = logging.getLogger(__name__)

FINANCIAL_TABLES = sorted(TABLE_COLUMNS.keys())

_MODEL_MAP = {
    "financial_per_share": FinancialPerShare,
    "financial_balance_sheet": FinancialBalanceSheet,
    "financial_income_sheet": FinancialIncomeSheet,
    "financial_cash_flow": FinancialCashFlow,
    "financial_ratio": FinancialRatio,
    "financial_holdings": FinancialHoldings,
}


class FinancialRepository:
    async def get_symbol_data(
        self,
        session: AsyncSession,
        symbol: str,
        start: date | None = None,
        end: date | None = None,
    ) -> list[dict]:
        merged: dict[tuple[str, date], dict] = {}

        for table_name in FINANCIAL_TABLES:
            model = _MODEL_MAP[table_name]
            stmt = select(model).where(model.symbol == symbol)
            if start:
                stmt = stmt.where(model.report_date >= start)
            if end:
                stmt = stmt.where(model.report_date <= end)
            stmt = stmt.order_by(model.report_date)

            result = await session.execute(stmt)
            rows = result.scalars().all()

            for row in rows:
                key = (row.symbol, row.report_date)
                if key not in merged:
                    merged[key] = {
                        "symbol": row.symbol,
                        "report_date": row.report_date,
                    }
                for attr_prop in row.__mapper__.column_attrs:
                    if attr_prop.key not in ("symbol", "report_date", "source", "updated_at"):
                        merged[key][attr_prop.key] = getattr(row, attr_prop.key)

        return [merged[k] for k in sorted(merged, key=lambda x: x[1])]

    async def query_filtered(
        self,
        session: AsyncSession,
        primary_table: str,
        where_clauses: list,
        params: list,
    ) -> list[dict]:
        model = _MODEL_MAP[primary_table]
        stmt = select(model.symbol, model.report_date)
        for clause in where_clauses:
            stmt = stmt.where(clause)
        stmt = stmt.order_by(model.symbol, model.report_date)

        result = await session.execute(stmt)
        return [{"symbol": r.symbol, "report_date": r.report_date} for r in result]

    async def fetch_symbol_rows(
        self, session: AsyncSession, table: str, symbol: str, report_dates: list[date]
    ) -> list[dict]:
        model = _MODEL_MAP[table]
        stmt = select(model).where(
            model.symbol == symbol,
            model.report_date.in_(report_dates),
        )
        result = await session.execute(stmt)
        rows = result.scalars().all()
        row_dicts = []
        for row in rows:
            d = {"symbol": row.symbol, "report_date": row.report_date}
            for attr_prop in row.__mapper__.column_attrs:
                if attr_prop.key not in ("symbol", "report_date", "source", "updated_at"):
                    d[attr_prop.key] = getattr(row, attr_prop.key)
            row_dicts.append(d)
        return row_dicts


financial_repository = FinancialRepository()
