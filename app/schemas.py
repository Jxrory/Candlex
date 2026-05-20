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


class StockInfoRecord(BaseModel):
    symbol: str
    name: str
    market: str
    list_date: date | None = None
    list_status: str | None = None
    industry: str | None = None
    sector: str | None = None


class FinancialIndicatorRecord(BaseModel):
    symbol: str
    report_date: date
    data: dict


class BalanceSheetRecord(BaseModel):
    symbol: str
    report_date: date
    data: dict


class ProfitSheetRecord(BaseModel):
    symbol: str
    report_date: date
    data: dict


class CashFlowSheetRecord(BaseModel):
    symbol: str
    report_date: date
    data: dict
