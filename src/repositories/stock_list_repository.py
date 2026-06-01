import logging

import asyncpg

from src.schemas.schemas import StockInfoRecord

logger = logging.getLogger(__name__)


class StockListRepository:
    async def get_all(
        self, conn: asyncpg.Connection, market: str | None = None
    ) -> list[StockInfoRecord]:
        if market:
            query = "SELECT symbol, name, market, list_date, list_status, industry, sector FROM stock_info WHERE market = $1 ORDER BY symbol"
            params = [market]
        else:
            query = "SELECT symbol, name, market, list_date, list_status, industry, sector FROM stock_info ORDER BY symbol"
            params = []

        rows = await conn.fetch(query, *params)
        return [
            StockInfoRecord(
                symbol=r["symbol"],
                name=r["name"],
                market=r["market"],
                list_date=r["list_date"],
                list_status=r["list_status"],
                industry=r["industry"],
                sector=r["sector"],
            )
            for r in rows
        ]

    async def upsert_many(
        self, conn: asyncpg.Connection, rows: list[tuple]
    ) -> int:
        if not rows:
            return 0
        await conn.executemany(
            """INSERT INTO stock_info (symbol, name, market, list_date, list_status, industry, sector)
               VALUES ($1,$2,$3,$4,$5,$6,$7)
               ON CONFLICT (symbol) DO UPDATE SET
                   name = EXCLUDED.name,
                   list_date = COALESCE(EXCLUDED.list_date, stock_info.list_date),
                   list_status = COALESCE(EXCLUDED.list_status, stock_info.list_status),
                   industry = COALESCE(EXCLUDED.industry, stock_info.industry),
                   sector = COALESCE(EXCLUDED.sector, stock_info.sector),
                   updated_at = NOW()""",
            rows,
        )
        return len(rows)

    async def get_next_pending(
        self, conn: asyncpg.Connection
    ) -> str | None:
        row = await conn.fetchrow(
            "SELECT symbol FROM stock_info "
            "WHERE list_status IS NULL "
            "LIMIT 1"
        )
        return row["symbol"] if row else None

    async def mark_synced(
        self, conn: asyncpg.Connection, symbol: str
    ) -> None:
        await conn.execute(
            "UPDATE stock_info SET list_status = 'SYNCED', list_date = NOW() WHERE symbol = $1",
            symbol,
        )


stock_list_repository = StockListRepository()
