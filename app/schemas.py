from datetime import date
from pydantic import BaseModel


class KlineRecord(BaseModel):
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int | None = None
    amount: float | None = None


class DividendRecord(BaseModel):
    ex_date: date
    cash_dividend: float | None = None
    stock_dividend: float | None = None
    capitalization: float | None = None
    rights_ratio: float | None = None
    rights_price: float | None = None
    event_type: str
