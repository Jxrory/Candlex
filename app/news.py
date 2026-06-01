import logging
from datetime import datetime

import asyncpg

from app.schemas import NewsRecord
from app.sources.news import NewsSource

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
        query = "SELECT symbol, title, content, publish_time, source_name, url FROM news WHERE symbol = $1"
        params: list = [symbol]
        if start:
            query += " AND publish_time >= $" + str(len(params) + 1)
            params.append(start)
        if end:
            query += " AND publish_time <= $" + str(len(params) + 1)
            params.append(end)
        query += " ORDER BY publish_time DESC"

        rows = await conn.fetch(query, *params)

        return [NewsRecord(**dict(r)) for r in rows]

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

        await conn.executemany(
            """INSERT INTO news (symbol, title, content, publish_time, source_name, url)
               VALUES ($1, $2, $3, $4, $5, $6)
               ON CONFLICT (symbol, url) DO UPDATE SET
                   title = EXCLUDED.title,
                   content = EXCLUDED.content,
                   publish_time = EXCLUDED.publish_time,
                   source_name = EXCLUDED.source_name,
                   updated_at = NOW()""",
            rows,
        )
        return len(rows)


news_service = NewsService()
