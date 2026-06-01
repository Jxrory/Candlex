import logging
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.models.kline import KlineData
from src.schemas.schemas import KlineRecord

logger = logging.getLogger(__name__)


class KlineRepository:
    async def get_cached(
        self, session: AsyncSession, symbol: str, start: date, end: date
    ) -> list[KlineRecord]:
        stmt = select(KlineData).where(
            KlineData.symbol == symbol,
            KlineData.date.between(start, end),
        ).order_by(KlineData.date)
        result = await session.execute(stmt)
        rows = result.scalars().all()
        return [
            KlineRecord(
                date=r.date, open=float(r.open) if r.open is not None else 0.0,
                high=float(r.high) if r.high is not None else 0.0,
                low=float(r.low) if r.low is not None else 0.0,
                close=float(r.close) if r.close is not None else 0.0,
                volume=int(r.volume) if r.volume is not None else None,
                amount=float(r.amount) if r.amount is not None else None,
            )
            for r in rows
        ]

    async def upsert_many(
        self, session: AsyncSession, rows: list[tuple]
    ) -> None:
        if not rows:
            return
        stmt = pg_insert(KlineData).values([
            {
                "symbol": r[0], "date": r[1],
                "open": r[2], "high": r[3], "low": r[4], "close": r[5],
                "volume": r[6], "amount": r[7], "source": r[8],
            }
            for r in rows
        ])
        stmt = stmt.on_conflict_do_update(
            index_elements=["symbol", "date"],
            set_={
                "open": stmt.excluded.open,
                "high": stmt.excluded.high,
                "low": stmt.excluded.low,
                "close": stmt.excluded.close,
                "volume": stmt.excluded.volume,
                "amount": stmt.excluded.amount,
                "source": stmt.excluded.source,
            },
        )
        await session.execute(stmt)


kline_repository = KlineRepository()
