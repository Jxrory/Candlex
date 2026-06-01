import logging
from datetime import date, timedelta
import asyncpg
import pandas as pd

from app.database import get_pool
from app.schemas import DividendRecord
from app.sources.base import BaseSource
from app.sources.dividend import DividendSource
from app.sources.mootdx_dividend import MootdxDividendSource

logger = logging.getLogger(__name__)


def _adjustment_ratio(
    prev_close: float,
    cash_dividend: float,
    stock_dividend: float,
    capitalization: float,
    rights_ratio: float,
    rights_price: float | None,
) -> float:
    C = prev_close
    D = cash_dividend or 0.0
    Rs = stock_dividend or 0.0
    Rc = capitalization or 0.0
    Rr = rights_ratio or 0.0
    Pr = rights_price or 0.0

    denominator = C * (1 + Rs + Rc + Rr)
    if denominator == 0:
        return 1.0
    adj = (C + Pr * Rr - D) / denominator
    return round(adj, 6)


def compute_factor(
    pairs: list[tuple[date, float]], kline_date: date, mode: str
) -> float:
    qfq = 1.0
    hfq = 1.0
    for ex_date, adj in pairs:
        if ex_date > kline_date:
            qfq *= adj
        if ex_date <= kline_date:
            hfq /= adj
    return qfq if mode == "qfq" else hfq


class DividendService:
    def __init__(self):
        self.sources: list[BaseSource] = [MootdxDividendSource(), DividendSource()]

    async def get_events(
        self,
        pool: asyncpg.Pool,
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

        async with pool.acquire() as conn:
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
        self, pool: asyncpg.Pool, symbol: str
    ) -> dict[date, float]:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT ex_date, adj_ratio FROM corporate_events
                   WHERE symbol = $1 AND adj_ratio IS NOT NULL
                   ORDER BY ex_date""",
                symbol,
            )
        return {r["ex_date"]: float(r["adj_ratio"]) for r in rows}

    async def _fetch_from_sources(self, symbol: str) -> tuple[pd.DataFrame, str]:
        for source in self.sources:
            try:
                df = await source.fetch(symbol)
                if not df.empty:
                    logger.info("dividend data for %s from %s (%d events)", symbol, source.name, len(df))
                    return df, source.name
            except Exception as e:
                logger.warning("dividend source %s failed for %s: %s", source.name, symbol, e)
                continue
        return pd.DataFrame(), ""

    async def sync_symbol(
        self, pool: asyncpg.Pool, symbol: str
    ) -> int:
        df, source_name = await self._fetch_from_sources(symbol)
        if df.empty:
            return 0

        ex_dates = [row["ex_date"] for _, row in df.iterrows()]
        prev_close_map = await self._batch_get_prev_close(pool, symbol, ex_dates)

        rows: list[tuple] = []
        for _, row in df.iterrows():
            ex_date = row["ex_date"]
            cd = row["cash_dividend"]
            sd = row["stock_dividend"]
            cap = row["capitalization"]
            rr = row["rights_ratio"]
            rp = row["rights_price"]
            et = row["event_type"]

            prev_close = prev_close_map.get(ex_date)
            adj = None
            if prev_close is not None:
                adj = _adjustment_ratio(prev_close, cd, sd, cap, rr, rp)

            rows.append((
                symbol, ex_date, cd, sd, cap, rr, rp,
                prev_close, adj, et, source_name,
            ))

        async with pool.acquire() as conn:
            await conn.executemany(
                """INSERT INTO corporate_events
                   (symbol, ex_date, cash_dividend, stock_dividend, capitalization,
                    rights_ratio, rights_price, prev_close, adj_ratio, event_type, source)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
                   ON CONFLICT (symbol, ex_date, event_type) DO NOTHING""",
                rows,
            )
        return len(rows)

    async def _batch_get_prev_close(
        self, pool: asyncpg.Pool, symbol: str, ex_dates: list[date]
    ) -> dict[date, float | None]:
        if not ex_dates:
            return {}
        async with pool.acquire() as conn:
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

    async def _get_prev_close(
        self, pool: asyncpg.Pool, symbol: str, ex_date: date
    ) -> float | None:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """SELECT close FROM kline_data
                   WHERE symbol = $1 AND date < $2
                   ORDER BY date DESC LIMIT 1""",
                symbol, ex_date,
            )
        return float(row["close"]) if row and row["close"] is not None else None

    async def ensure_fresh(self, pool: asyncpg.Pool, symbol: str) -> None:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """SELECT MAX(ex_date) as max_ex FROM corporate_events
                   WHERE symbol = $1""",
                symbol,
            )
        if row and row["max_ex"]:
            last_event = row["max_ex"]
            three_months_ago = date.today() - timedelta(days=95)
            if last_event >= three_months_ago:
                return
        await self.sync_symbol(pool, symbol)


dividend_service = DividendService()
