import logging
from datetime import datetime

import asyncpg

from src.schemas.schemas import NewsRecord

logger = logging.getLogger(__name__)


class NewsRepository:
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

    async def upsert_many(
        self, conn: asyncpg.Connection, rows: list[tuple]
    ) -> int:
        if not rows:
            return 0
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


news_repository = NewsRepository()
