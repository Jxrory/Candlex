import asyncio
import logging
from datetime import date

import asyncpg

from src.models.financial_mapping import TABLE_COLUMNS

logger = logging.getLogger(__name__)

FINANCIAL_TABLES = sorted(TABLE_COLUMNS.keys())


class FinancialRepository:
    async def get_symbol_data(
        self,
        conn: asyncpg.Connection,
        symbol: str,
        start: date | None = None,
        end: date | None = None,
    ) -> list[dict]:
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

    async def query_filtered(
        self,
        conn: asyncpg.Connection,
        primary_table: str,
        where_clauses: list[str],
        params: list,
    ) -> list[asyncpg.Record]:
        query = f"SELECT symbol, report_date FROM {primary_table}"
        query += " WHERE " + " AND ".join(where_clauses)
        query += " ORDER BY symbol, report_date"
        return await conn.fetch(query, *params)

    async def fetch_symbol_rows(
        self, conn: asyncpg.Connection, table: str, symbol: str, report_dates: list[date]
    ) -> list[dict]:
        rows = await conn.fetch(
            f"SELECT * FROM {table} WHERE symbol = $1 AND report_date = ANY($2)",
            symbol, report_dates,
        )
        return [dict(r) for r in rows]


financial_repository = FinancialRepository()
