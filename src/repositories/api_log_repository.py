import logging

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.api_log import ApiRequestLog

logger = logging.getLogger(__name__)


class ApiLogRepository:
    async def insert(
        self, session: AsyncSession, entry: dict
    ) -> None:
        record = ApiRequestLog(
            api_name=entry["api_name"],
            symbol=entry.get("symbol"),
            params=entry.get("params"),
            status=entry["status"],
            row_count=entry.get("row_count"),
            duration_ms=entry.get("duration_ms"),
            error_msg=entry.get("error_msg"),
        )
        session.add(record)


api_log_repository = ApiLogRepository()
