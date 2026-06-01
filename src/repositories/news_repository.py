import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.models.news import News
from src.schemas.schemas import NewsRecord

logger = logging.getLogger(__name__)


class NewsRepository:
    async def get_news(
        self,
        session: AsyncSession,
        symbol: str,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[NewsRecord]:
        stmt = select(News).where(News.symbol == symbol)
        if start:
            stmt = stmt.where(News.publish_time >= start)
        if end:
            stmt = stmt.where(News.publish_time <= end)
        stmt = stmt.order_by(News.publish_time.desc())

        result = await session.execute(stmt)
        rows = result.scalars().all()
        return [
            NewsRecord(
                symbol=r.symbol, title=r.title, content=r.content,
                publish_time=r.publish_time, source_name=r.source_name,
                url=r.url,
            )
            for r in rows
        ]

    async def upsert_many(
        self, session: AsyncSession, rows: list[tuple]
    ) -> int:
        if not rows:
            return 0
        stmt = pg_insert(News).values([
            {
                "symbol": r[0], "title": r[1], "content": r[2],
                "publish_time": r[3], "source_name": r[4], "url": r[5],
            }
            for r in rows
        ])
        stmt = stmt.on_conflict_do_update(
            index_elements=["symbol", "url"],
            set_={
                "title": stmt.excluded.title,
                "content": stmt.excluded.content,
                "publish_time": stmt.excluded.publish_time,
                "source_name": stmt.excluded.source_name,
            },
        )
        await session.execute(stmt)
        return len(rows)


news_repository = NewsRepository()
