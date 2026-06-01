from sqlalchemy import Date, DateTime
from sqlalchemy.sql import func
from src.models.base import Base
from sqlalchemy.orm import Mapped, mapped_column


class TradeCalendar(Base):
    __tablename__ = "trade_calendar"

    trade_date: Mapped[Date] = mapped_column(Date, primary_key=True)
    updated_at = mapped_column(DateTime(timezone=True), server_default=func.now())
