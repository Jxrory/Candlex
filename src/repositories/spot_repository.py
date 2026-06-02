import json
import logging
from datetime import datetime

from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.models.spot import SpotSnapshot

logger = logging.getLogger(__name__)

_BATCH_SIZE = 500


class SpotRepository:
    async def get_latest_by_symbol(
        self, session: AsyncSession, symbol: str
    ) -> dict | None:
        stmt = select(SpotSnapshot.data).where(
            SpotSnapshot.symbol == symbol
        ).order_by(SpotSnapshot.snapshot_time.desc()).limit(1)
        result = await session.execute(stmt)
        row = result.one_or_none()
        if not row:
            return None
        data = row[0]
        if isinstance(data, str):
            data = json.loads(data)
        if isinstance(data, dict):
            return data
        return dict(data)

    async def get_all_latest(
        self, session: AsyncSession
    ) -> list[dict]:
        subq = select(
            SpotSnapshot.symbol,
            sa_func.max(SpotSnapshot.snapshot_time).label("max_time"),
        ).group_by(SpotSnapshot.symbol).subquery()

        stmt = select(SpotSnapshot).join(
            subq,
            (SpotSnapshot.symbol == subq.c.symbol) &
            (SpotSnapshot.snapshot_time == subq.c.max_time),
        ).order_by(SpotSnapshot.symbol)

        result = await session.execute(stmt)
        rows = result.scalars().all()
        return [{"symbol": r.symbol, "data": r.data} for r in rows]

    async def upsert_many(
        self, session: AsyncSession, rows: list[tuple]
    ) -> None:
        if not rows:
            return
        for i in range(0, len(rows), _BATCH_SIZE):
            chunk = rows[i : i + _BATCH_SIZE]
            stmt = pg_insert(SpotSnapshot).values([
                {
                    "symbol": r[0], "snapshot_time": r[1],
                    "data": r[2], "source": r[3],
                }
                for r in chunk
            ])
            stmt = stmt.on_conflict_do_update(
                index_elements=["symbol", "snapshot_time"],
                set_={"data": stmt.excluded.data, "source": stmt.excluded.source},
            )
            await session.execute(stmt)


spot_repository = SpotRepository()
