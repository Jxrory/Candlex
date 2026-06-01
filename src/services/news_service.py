import logging
from datetime import datetime

import asyncpg

from src.repositories.news_repository import news_repository
from src.schemas.schemas import NewsRecord
from src.tools.sources.news import NewsSource

logger = logging.getLogger(__name__)


class NewsService:
    def __init__(self):
        self.source = NewsSource()

    async def get_news(
        self,
        conn: asyncpg.Connection,
        symbol: str,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[NewsRecord]:
        return await news_repository.get_news(conn, symbol, start, end)

    async def sync_symbol(self, conn: asyncpg.Connection, symbol: str) -> int:
        df = await self.source.fetch(symbol)
        if df.empty:
            return 0

        rows: list[tuple] = []
        for _, row in df.iterrows():
            rows.append((
                row["symbol"], row["title"], row["content"],
                row["publish_time"], row["source_name"], row["url"],
            ))

        return await news_repository.upsert_many(conn, rows)


news_service = NewsService()
