import logging

import asyncpg

logger = logging.getLogger(__name__)


class ApiLogRepository:
    async def insert(
        self, conn: asyncpg.Connection, entry: dict
    ) -> None:
        await conn.execute(
            """INSERT INTO api_request_log
               (api_name, symbol, params, status, row_count, duration_ms, error_msg)
               VALUES ($1,$2,$3::jsonb,$4,$5,$6,$7)""",
            entry["api_name"], entry["symbol"], entry["params"],
            entry["status"], entry["row_count"], entry["duration_ms"],
            entry["error_msg"],
        )


api_log_repository = ApiLogRepository()
