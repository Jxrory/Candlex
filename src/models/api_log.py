from sqlalchemy import String, BigInteger, Integer, DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from src.models.base import Base
from sqlalchemy.orm import Mapped, mapped_column


class ApiRequestLog(Base):
    __tablename__ = "api_request_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    created_at = mapped_column(DateTime(timezone=True), primary_key=True, server_default=func.now())
    api_name: Mapped[str] = mapped_column(String(100))
    symbol: Mapped[str | None] = mapped_column(String(10))
    params: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(20))
    row_count: Mapped[int | None] = mapped_column(Integer)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    error_msg: Mapped[str | None] = mapped_column(Text)
