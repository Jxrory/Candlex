from sqlalchemy import String, Date, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column


class FinancialBaseMixin:
    symbol: Mapped[str] = mapped_column(String(10), primary_key=True)
    report_date: Mapped[Date] = mapped_column(Date, primary_key=True)
    source: Mapped[str] = mapped_column(String(20), default="mootdx")
    updated_at = mapped_column(DateTime(timezone=True), server_default=func.now())
