import logging
from datetime import date, timedelta

import asyncpg
import pandas as pd

from src.repositories.dividend_repository import dividend_repository
from src.schemas.schemas import DividendRecord
from src.tools.sources.base import BaseSource
from src.tools.sources.dividend import DividendSource
from src.tools.sources.mootdx_dividend import MootdxDividendSource

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
        conn: asyncpg.Connection,
        symbol: str,
        start: date | None = None,
        end: date | None = None,
    ) -> list[DividendRecord]:
        return await dividend_repository.get_events(conn, symbol, start, end)

    async def get_adj_ratios(
        self, conn: asyncpg.Connection, symbol: str
    ) -> dict[date, float]:
        return await dividend_repository.get_adj_ratios(conn, symbol)

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
        self, conn: asyncpg.Connection, symbol: str
    ) -> int:
        df, source_name = await self._fetch_from_sources(symbol)
        if df.empty:
            return 0

        ex_dates = [row["ex_date"] for _, row in df.iterrows()]
        prev_close_map = await dividend_repository.get_prev_close_batch(conn, symbol, ex_dates)

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

        return await dividend_repository.upsert_many(conn, rows)

    async def ensure_fresh(self, conn: asyncpg.Connection, symbol: str) -> None:
        max_ex = await dividend_repository.get_max_ex_date(conn, symbol)
        if max_ex and max_ex >= date.today() - timedelta(days=95):
            return
        await self.sync_symbol(conn, symbol)


dividend_service = DividendService()
