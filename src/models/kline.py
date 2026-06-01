from sqlalchemy import String, Date, Numeric, BigInteger
from src.models.base import Base
from sqlalchemy.orm import Mapped, mapped_column


class KlineData(Base):
    __tablename__ = "kline_data"

    symbol: Mapped[str] = mapped_column(String(10), primary_key=True)
    date: Mapped[Date] = mapped_column(Date, primary_key=True)
    open: Mapped[float | None] = mapped_column(Numeric(10, 3))
    high: Mapped[float | None] = mapped_column(Numeric(10, 3))
    low: Mapped[float | None] = mapped_column(Numeric(10, 3))
    close: Mapped[float | None] = mapped_column(Numeric(10, 3))
    volume: Mapped[int | None] = mapped_column(BigInteger)
    amount: Mapped[float | None] = mapped_column(Numeric(15, 2))
    source: Mapped[str] = mapped_column(String(50))

    def __repr__(self):
        return f"<KlineData {self.symbol} {self.date}>"
