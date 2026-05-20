import json
import logging
from datetime import date

import asyncpg
import pandas as pd

from app.schemas import CashFlowSheetRecord
from app.sources.cash_flow_sheet import CashFlowSheetSource

logger = logging.getLogger(__name__)


class CashFlowSheetService:
    def __init__(self):
        self.source = CashFlowSheetSource()

    async def get_cash_flow_sheets(
        self,
        pool: asyncpg.Pool,
        symbol: str,
        start: date | None = None,
        end: date | None = None,
    ) -> list[CashFlowSheetRecord]:
        query = "SELECT symbol, report_date, data FROM cash_flow_sheets WHERE symbol = $1"
        params: list = [symbol]
        if start:
            query += " AND report_date >= $" + str(len(params) + 1)
            params.append(start)
        if end:
            query += " AND report_date <= $" + str(len(params) + 1)
            params.append(end)
        query += " ORDER BY report_date"

        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        return [
            CashFlowSheetRecord(
                symbol=r["symbol"],
                report_date=r["report_date"],
                data=json.loads(r["data"]) if isinstance(r["data"], str) else dict(r["data"]),
            )
            for r in rows
        ]

    async def sync_symbol(self, pool: asyncpg.Pool, symbol: str) -> int:
        df = await self.source.fetch(symbol)
        if df.empty:
            return 0

        rows: list[tuple] = []
        for _, row in df.iterrows():
            data_json = json.dumps(row["data"], ensure_ascii=False, default=str)
            rows.append((symbol, row["report_date"], data_json, self.source.name))

        async with pool.acquire() as conn:
            await conn.executemany(
                """INSERT INTO cash_flow_sheets (symbol, report_date, data, source)
                   VALUES ($1, $2, $3::jsonb, $4)
                   ON CONFLICT (symbol, report_date) DO UPDATE SET
                       data = EXCLUDED.data,
                       source = EXCLUDED.source,
                       updated_at = NOW()""",
                rows,
            )
        return len(rows)


cash_flow_sheet_service = CashFlowSheetService()
