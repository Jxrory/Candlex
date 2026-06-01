import logging

import asyncpg
import pandas as pd

from src.repositories.stock_list_repository import stock_list_repository
from src.schemas.schemas import StockInfoRecord
from src.tools.sources.stock_list import StockListSource

logger = logging.getLogger(__name__)


class StockListService:
    def __init__(self):
        self.source = StockListSource()

    async def get_stocks(
        self, conn: asyncpg.Connection, market: str | None = None
    ) -> list[StockInfoRecord]:
        return await stock_list_repository.get_all(conn, market)

    async def sync(self, conn: asyncpg.Connection, market: str) -> int:
        df = await self.source.fetch(market)
        if df.empty:
            return 0

        def _nan(val):
            return None if pd.isna(val) else val

        rows: list[tuple] = []
        for _, row in df.iterrows():
            rows.append((
                row["symbol"],
                row["name"],
                row["market"],
                _nan(row.get("list_date")),
                _nan(row.get("list_status")),
                _nan(row.get("industry")),
                _nan(row.get("sector")),
            ))

        return await stock_list_repository.upsert_many(conn, rows)


stock_list_service = StockListService()
