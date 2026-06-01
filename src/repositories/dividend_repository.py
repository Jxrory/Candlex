import logging
from datetime import date

from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.models.dividend import CorporateEvent
from src.models.kline import KlineData
from src.schemas.schemas import DividendRecord

logger = logging.getLogger(__name__)


class DividendRepository:
    async def get_events(
        self,
        session: AsyncSession,
        symbol: str,
        start: date | None = None,
        end: date | None = None,
    ) -> list[DividendRecord]:
        stmt = select(CorporateEvent).where(CorporateEvent.symbol == symbol)
        if start:
            stmt = stmt.where(CorporateEvent.ex_date >= start)
        if end:
            stmt = stmt.where(CorporateEvent.ex_date <= end)
        stmt = stmt.order_by(CorporateEvent.ex_date)

        result = await session.execute(stmt)
        rows = result.scalars().all()
        return [
            DividendRecord(
                ex_date=r.ex_date,
                cash_dividend=float(r.cash_dividend) if r.cash_dividend is not None else None,
                stock_dividend=float(r.stock_dividend) if r.stock_dividend is not None else None,
                capitalization=float(r.capitalization) if r.capitalization is not None else None,
                rights_ratio=float(r.rights_ratio) if r.rights_ratio is not None else None,
                rights_price=float(r.rights_price) if r.rights_price is not None else None,
                event_type=r.event_type,
            )
            for r in rows
        ]

    async def get_adj_ratios(
        self, session: AsyncSession, symbol: str
    ) -> dict[date, float]:
        stmt = select(
            CorporateEvent.ex_date, CorporateEvent.adj_ratio
        ).where(
            CorporateEvent.symbol == symbol,
            CorporateEvent.adj_ratio.is_not(None),
        ).order_by(CorporateEvent.ex_date)

        result = await session.execute(stmt)
        return {r.ex_date: float(r.adj_ratio) for r in result}

    async def get_prev_close_batch(
        self, session: AsyncSession, symbol: str, ex_dates: list[date]
    ) -> dict[date, float | None]:
        if not ex_dates:
            return {}
        from sqlalchemy import literal, Text
        from sqlalchemy.dialects.postgresql import array

        close_map: dict[date, float | None] = {}
        for ex_date in ex_dates:
            subq = select(KlineData.close).where(
                KlineData.symbol == symbol,
                KlineData.date < ex_date,
            ).order_by(KlineData.date.desc()).limit(1)
            result = await session.execute(subq)
            row = result.one_or_none()
            close_map[ex_date] = float(row[0]) if row and row[0] is not None else None
        return close_map

    async def get_max_ex_date(
        self, session: AsyncSession, symbol: str
    ) -> date | None:
        stmt = select(sa_func.max(CorporateEvent.ex_date)).where(
            CorporateEvent.symbol == symbol
        )
        result = await session.execute(stmt)
        return result.scalar()

    async def upsert_many(
        self, session: AsyncSession, rows: list[tuple]
    ) -> int:
        if not rows:
            return 0
        stmt = pg_insert(CorporateEvent).values([
            {
                "symbol": r[0], "ex_date": r[1],
                "cash_dividend": r[2], "stock_dividend": r[3],
                "capitalization": r[4], "rights_ratio": r[5],
                "rights_price": r[6], "prev_close": r[7],
                "adj_ratio": r[8], "event_type": r[9], "source": r[10],
            }
            for r in rows
        ])
        stmt = stmt.on_conflict_do_nothing(
            index_elements=["symbol", "ex_date", "event_type"],
        )
        await session.execute(stmt)
        return len(rows)


dividend_repository = DividendRepository()
