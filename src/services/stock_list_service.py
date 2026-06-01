import logging

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.stock_list_repository import stock_list_repository
from src.schemas.schemas import StockInfoRecord
from src.tools.sources.stock_list import StockListSource
from src.tools.sources.mootdx import MootdxStockListSource

logger = logging.getLogger(__name__)

SOURCES: dict[str, StockListSource | MootdxStockListSource] = {
    "akshare": StockListSource(),
    "mootdx": MootdxStockListSource(),
}

SOURCE_PRIORITY: list[str] = ["akshare", "mootdx"]


class StockListService:
    async def get_stocks(
        self, session: AsyncSession, market: str | None = None
    ) -> list[StockInfoRecord]:
        return await stock_list_repository.get_all(session, market)

    async def sync(self, session: AsyncSession, market: str) -> int:
        df = pd.DataFrame()
        used_source: str | None = None

        for source_name in SOURCE_PRIORITY:
            src = SOURCES.get(source_name)
            if not src:
                continue
            try:
                df = await src.fetch(market)
                if not df.empty:
                    used_source = source_name
                    break
            except Exception as e:
                logger.error("stock list source %s failed: %s", source_name, e)
                continue

        if df.empty:
            logger.warning("all stock list sources failed for market %s", market)
            return 0

        logger.info("stock list synced from %s: %d rows", used_source, len(df))

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

        return await stock_list_repository.upsert_many(session, rows)


stock_list_service = StockListService()
