import logging
from datetime import date

import asyncpg

from src.schemas.schemas import DividendRecord

logger = logging.getLogger(__name__)


class DividendRepository:
    async def get_events(
        self,
        conn: asyncpg.Connection,
        symbol: str,
        start: date | None = None,
        end: date | None = None,
    ) -> list[DividendRecord]:
        query = """SELECT ex_date, cash_dividend, stock_dividend, capitalization,
                          rights_ratio, rights_price, event_type
                   FROM corporate_events
                   WHERE symbol = $1"""
        params: list = [symbol]
        if start:
            query += " AND ex_date >= $" + str(len(params) + 1)
            params.append(start)
        if end:
            query += " AND ex_date <= $" + str(len(params) + 1)
            params.append(end)
        query += " ORDER BY ex_date"

        rows = await conn.fetch(query, *params)
        return [
            DividendRecord(
                ex_date=r["ex_date"],
                cash_dividend=float(r["cash_dividend"]) if r["cash_dividend"] is not None else None,
                stock_dividend=float(r["stock_dividend"]) if r["stock_dividend"] is not None else None,
                capitalization=float(r["capitalization"]) if r["capitalization"] is not None else None,
                rights_ratio=float(r["rights_ratio"]) if r["rights_ratio"] is not None else None,
                rights_price=float(r["rights_price"]) if r["rights_price"] is not None else None,
                event_type=r["event_type"],
            )
            for r in rows
        ]

    async def get_adj_ratios(
        self, conn: asyncpg.Connection, symbol: str
    ) -> dict[date, float]:
        rows = await conn.fetch(
            """SELECT ex_date, adj_ratio FROM corporate_events
               WHERE symbol = $1 AND adj_ratio IS NOT NULL
               ORDER BY ex_date""",
            symbol,
        )
        return {r["ex_date"]: float(r["adj_ratio"]) for r in rows}

    async def get_prev_close_batch(
        self, conn: asyncpg.Connection, symbol: str, ex_dates: list[date]
    ) -> dict[date, float | None]:
        if not ex_dates:
            return {}
        rows = await conn.fetch(
            """SELECT d.ex_date, k.close FROM
               (SELECT unnest($2::date[]) AS ex_date) d
               LEFT JOIN LATERAL (
                   SELECT close FROM kline_data
                   WHERE symbol = $1 AND date < d.ex_date
                   ORDER BY date DESC LIMIT 1
               ) k ON true""",
            symbol, ex_dates,
        )
        return {r["ex_date"]: float(r["close"]) if r["close"] is not None else None for r in rows}

    async def get_max_ex_date(
        self, conn: asyncpg.Connection, symbol: str
    ) -> date | None:
        row = await conn.fetchrow(
            """SELECT MAX(ex_date) as max_ex FROM corporate_events
               WHERE symbol = $1""",
            symbol,
        )
        return row["max_ex"] if row else None

    async def upsert_many(
        self, conn: asyncpg.Connection, rows: list[tuple]
    ) -> int:
        if not rows:
            return 0
        await conn.executemany(
            """INSERT INTO corporate_events
               (symbol, ex_date, cash_dividend, stock_dividend, capitalization,
                rights_ratio, rights_price, prev_close, adj_ratio, event_type, source)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
               ON CONFLICT (symbol, ex_date, event_type) DO NOTHING""",
            rows,
        )
        return len(rows)


dividend_repository = DividendRepository()
