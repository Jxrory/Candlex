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
    factor_qfq: float | None = None
    factor_hfq: float | None = None
