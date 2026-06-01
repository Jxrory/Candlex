import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.models.stock import StockInfo
from src.schemas.schemas import StockInfoRecord

logger = logging.getLogger(__name__)


class StockListRepository:
    async def get_all(
        self, session: AsyncSession, market: str | None = None
    ) -> list[StockInfoRecord]:
        stmt = select(
            StockInfo.symbol, StockInfo.name, StockInfo.market,
            StockInfo.list_date, StockInfo.list_status,
            StockInfo.industry, StockInfo.sector,
        )
        if market:
            stmt = stmt.where(StockInfo.market == market)
        stmt = stmt.order_by(StockInfo.symbol)

        result = await session.execute(stmt)
        rows = result.all()
        return [
            StockInfoRecord(
                symbol=r.symbol, name=r.name, market=r.market,
                list_date=r.list_date, list_status=r.list_status,
                industry=r.industry, sector=r.sector,
            )
            for r in rows
        ]

    async def upsert_many(
        self, session: AsyncSession, rows: list[tuple]
    ) -> int:
        if not rows:
            return 0
        stmt = pg_insert(StockInfo).values([
            {
                "symbol": r[0], "name": r[1], "market": r[2],
                "list_date": r[3], "list_status": r[4],
                "industry": r[5], "sector": r[6],
            }
            for r in rows
        ])
        stmt = stmt.on_conflict_do_update(
            index_elements=["symbol"],
            set_={
                "name": stmt.excluded.name,
                "list_date": stmt.excluded.list_date,
                "list_status": stmt.excluded.list_status,
                "industry": stmt.excluded.industry,
                "sector": stmt.excluded.sector,
            },
        )
        await session.execute(stmt)
        return len(rows)

    async def get_next_pending(
        self, session: AsyncSession
    ) -> str | None:
        stmt = select(StockInfo.symbol).where(
            StockInfo.list_status.is_(None)
        ).limit(1)
        result = await session.execute(stmt)
        row = result.one_or_none()
        return row[0] if row else None

    async def mark_synced(
        self, session: AsyncSession, symbol: str
    ) -> None:
        stmt = select(StockInfo).where(StockInfo.symbol == symbol)
        result = await session.execute(stmt)
        stock = result.scalar_one_or_none()
        if stock:
            stock.list_status = "SYNCED"


stock_list_repository = StockListRepository()
