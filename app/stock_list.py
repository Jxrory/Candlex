import logging
import asyncpg
import pandas as pd

from app.database import get_pool
from app.schemas import StockInfoRecord
from app.sources.stock_list import StockListSource

logger = logging.getLogger(__name__)


class StockListService:
    def __init__(self):
        self.source = StockListSource()

    async def get_stocks(
        self, pool: asyncpg.Pool, market: str | None = None
    ) -> list[StockInfoRecord]:
        if market:
            query = "SELECT symbol, name, market, list_date, list_status, industry, sector FROM stock_info WHERE market = $1 ORDER BY symbol"
            params = [market]
        else:
            query = "SELECT symbol, name, market, list_date, list_status, industry, sector FROM stock_info ORDER BY symbol"
            params = []

        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        return [
            StockInfoRecord(
                symbol=r["symbol"],
                name=r["name"],
                market=r["market"],
                list_date=r["list_date"],
                list_status=r["list_status"],
                industry=r["industry"],
                sector=r["sector"],
            )
            for r in rows
        ]

    async def sync(self, pool: asyncpg.Pool, market: str) -> int:
        df = await self.source.fetch(market)
        if df.empty:
            return 0

        rows: list[tuple] = []
        for _, row in df.iterrows():
            rows.append((
                row["symbol"],
                row["name"],
                row["market"],
                row.get("list_date"),
                row.get("list_status"),
                row.get("industry"),
                row.get("sector"),
            ))

        async with pool.acquire() as conn:
            await conn.executemany(
                """INSERT INTO stock_info (symbol, name, market, list_date, list_status, industry, sector)
                   VALUES ($1,$2,$3,$4,$5,$6,$7)
                   ON CONFLICT (symbol) DO UPDATE SET
                       name = EXCLUDED.name,
                       list_date = COALESCE(EXCLUDED.list_date, stock_info.list_date),
                       list_status = COALESCE(EXCLUDED.list_status, stock_info.list_status),
                       industry = COALESCE(EXCLUDED.industry, stock_info.industry),
                       sector = COALESCE(EXCLUDED.sector, stock_info.sector),
                       updated_at = NOW()""",
                rows,
            )
        return len(rows)


stock_list_service = StockListService()
