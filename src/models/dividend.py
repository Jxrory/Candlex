from sqlalchemy import String, Date, Numeric
from src.models.base import Base
from sqlalchemy.orm import Mapped, mapped_column


class CorporateEvent(Base):
    __tablename__ = "corporate_events"

    symbol: Mapped[str] = mapped_column(String(10), primary_key=True)
    ex_date: Mapped[Date] = mapped_column(Date, primary_key=True)
    event_type: Mapped[str] = mapped_column(String(50), primary_key=True)
    cash_dividend: Mapped[float | None] = mapped_column(Numeric(10, 6))
    stock_dividend: Mapped[float | None] = mapped_column(Numeric(10, 6))
    capitalization: Mapped[float | None] = mapped_column(Numeric(10, 6))
    rights_ratio: Mapped[float | None] = mapped_column(Numeric(10, 6))
    rights_price: Mapped[float | None] = mapped_column(Numeric(10, 4))
    prev_close: Mapped[float | None] = mapped_column(Numeric(10, 3))
    adj_ratio: Mapped[float | None] = mapped_column(Numeric(10, 6))
    source: Mapped[str] = mapped_column(String(50))
