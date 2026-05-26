import asyncio
import logging
from datetime import date

import asyncpg

from app.financial_v2_mapping import TABLE_COLUMNS, ENGLISH_TO_TABLE

logger = logging.getLogger(__name__)

FINANCIAL_TABLES = sorted(TABLE_COLUMNS.keys())


async def get_financial_data(
    pool: asyncpg.Pool,
    symbol: str,
    start: date | None = None,
    end: date | None = None,
) -> list[dict]:
    """
    Get complete financial data for one stock, merging all 6 tables.

    Returns list of flat dicts keyed by (symbol, report_date).
    """
    async def _fetch_table(table_name: str) -> list[dict]:
        query = f"SELECT * FROM {table_name} WHERE symbol = $1"
        params: list = [symbol]
        if start:
            query += f" AND report_date >= ${len(params) + 1}"
            params.append(start)
        if end:
            query += f" AND report_date <= ${len(params) + 1}"
            params.append(end)
        query += " ORDER BY report_date"

        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
        return [dict(r) for r in rows]

    results = await asyncio.gather(
        *[_fetch_table(t) for t in FINANCIAL_TABLES]
    )

    merged: dict[tuple[str, date], dict] = {}
    for table_name, rows in zip(FINANCIAL_TABLES, results):
        for row in rows:
            key = (row["symbol"], row["report_date"])
            if key not in merged:
                merged[key] = {
                    "symbol": row["symbol"],
                    "report_date": row["report_date"],
                }
            for k, v in row.items():
                if k not in ("symbol", "report_date", "source", "updated_at"):
                    merged[key][k] = v

    return [merged[k] for k in sorted(merged.keys(), key=lambda x: x[1])]


async def query_financial(
    pool: asyncpg.Pool,
    filters: dict[str, tuple[float | None, float | None]],
    report_date: date | None = None,
) -> list[dict]:
    """
    Cross-stock screening with min/max filters.

    filters: {english_col: (min_val, max_val)}
    Example: {"roe": (15.0, None), "debt_ratio": (None, 50.0)}

    Returns list of flat dicts (same shape as get_financial_data).
    """
    if not filters:
        return []

    table_filters: dict[str, dict[str, tuple[float | None, float | None]]] = {}
    for col_name, (min_val, max_val) in filters.items():
        table_name = ENGLISH_TO_TABLE.get(col_name)
        if table_name is None:
            logger.warning("unknown column for filtering: %s", col_name)
            continue
        table_filters.setdefault(table_name, {})[col_name] = (min_val, max_val)

    if not table_filters:
        return []

    primary_table = next(iter(table_filters))
    primary_filters = table_filters[primary_table]

    where_clauses: list[str] = []
    params: list = []
    param_idx = 1

    if report_date:
        where_clauses.append(f"report_date = ${param_idx}")
        params.append(report_date)
        param_idx += 1

    for col_name, (min_val, max_val) in primary_filters.items():
        if min_val is not None:
            where_clauses.append(f"{col_name} >= ${param_idx}")
            params.append(min_val)
            param_idx += 1
        if max_val is not None:
            where_clauses.append(f"{col_name} <= ${param_idx}")
            params.append(max_val)
            param_idx += 1

    if not where_clauses:
        return []

    query = f"SELECT symbol, report_date FROM {primary_table}"
    query += " WHERE " + " AND ".join(where_clauses)
    query += " ORDER BY symbol, report_date"

    async with pool.acquire() as conn:
        matching = await conn.fetch(query, *params)

    if not matching:
        return []

    async def _fetch_symbol_data(sym: str, rd: date) -> dict:
        merged: dict = {"symbol": sym, "report_date": rd}
        for tbl in FINANCIAL_TABLES:
            q = f"SELECT * FROM {tbl} WHERE symbol = $1 AND report_date = $2"
            async with pool.acquire() as conn:
                row = await conn.fetchrow(q, sym, rd)
            if row:
                for k, v in dict(row).items():
                    if k not in ("symbol", "report_date", "source", "updated_at"):
                        merged[k] = v
        return merged

    results = await asyncio.gather(
        *[_fetch_symbol_data(r["symbol"], r["report_date"]) for r in matching]
    )
    return results


class FinancialV2Service:
    async def get_financial_data(
        self,
        pool: asyncpg.Pool,
        symbol: str,
        start: date | None = None,
        end: date | None = None,
    ) -> list[dict]:
        return await get_financial_data(pool, symbol, start, end)

    async def query_financial(
        self,
        pool: asyncpg.Pool,
        filters: dict[str, tuple[float | None, float | None]],
        report_date: date | None = None,
    ) -> list[dict]:
        return await query_financial(pool, filters, report_date)


financial_v2_service = FinancialV2Service()

__all__ = ["financial_v2_service", "get_financial_data", "query_financial"]
