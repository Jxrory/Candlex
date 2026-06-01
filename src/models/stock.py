from sqlalchemy import String, Date, DateTime
from sqlalchemy.sql import func
from src.models.base import Base
from sqlalchemy.orm import Mapped, mapped_column


class StockInfo(Base):
    __tablename__ = "stock_info"

    symbol: Mapped[str] = mapped_column(String(10), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    market: Mapped[str] = mapped_column(String(10))
    list_date: Mapped[Date | None] = mapped_column(Date)
    list_status: Mapped[str | None] = mapped_column(String(20))
    industry: Mapped[str | None] = mapped_column(String(100))
    sector: Mapped[str | None] = mapped_column(String(100))
    updated_at = mapped_column(DateTime(timezone=True), server_default=func.now())
