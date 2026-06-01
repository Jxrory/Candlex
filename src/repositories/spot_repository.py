import json
import logging
from datetime import datetime

import asyncpg

logger = logging.getLogger(__name__)


class SpotRepository:
    async def get_latest_by_symbol(
        self, conn: asyncpg.Connection, symbol: str
    ) -> dict | None:
        row = await conn.fetchrow(
            """SELECT data FROM spot_snapshots
               WHERE symbol = $1
               ORDER BY snapshot_time DESC LIMIT 1""",
            symbol,
        )
        if not row:
            return None
        data = row["data"]
        if isinstance(data, str):
            data = json.loads(data)
        if isinstance(data, dict):
            return data
        return dict(data)

    async def get_all_latest(
        self, conn: asyncpg.Connection
    ) -> list[asyncpg.Record]:
        return await conn.fetch(
            """SELECT symbol, data FROM spot_snapshots
               WHERE snapshot_time = (
                   SELECT MAX(snapshot_time) FROM spot_snapshots
               ) ORDER BY symbol"""
        )

    async def upsert_many(
        self, conn: asyncpg.Connection, rows: list[tuple]
    ) -> None:
        if not rows:
            return
        await conn.executemany(
            """INSERT INTO spot_snapshots (symbol, snapshot_time, data, source)
               VALUES ($1, $2, $3::jsonb, $4)
               ON CONFLICT (symbol, snapshot_time) DO UPDATE SET
                   data = EXCLUDED.data,
                   source = EXCLUDED.source""",
            rows,
        )

    async def upsert_kline_many(
        self, conn: asyncpg.Connection, rows: list[tuple]
    ) -> None:
        if not rows:
            return
        await conn.executemany(
            """INSERT INTO kline_data (symbol, date, open, high, low, close, volume, amount, source)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
               ON CONFLICT (symbol, date) DO UPDATE SET
                   open = EXCLUDED.open,
                   high = EXCLUDED.high,
                   low = EXCLUDED.low,
                   close = EXCLUDED.close,
                   volume = EXCLUDED.volume,
                   amount = EXCLUDED.amount,
                   source = EXCLUDED.source""",
            rows,
        )


spot_repository = SpotRepository()
