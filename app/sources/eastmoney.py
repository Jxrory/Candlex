from datetime import date
import akshare as ak
import pandas as pd

from app.sources.base import BaseSource

COLUMN_MAP = {
    "日期": "date",
    "开盘": "open",
    "收盘": "close",
    "最高": "high",
    "最低": "low",
    "成交量": "volume",
    "成交额": "amount",
}


class EastMoneySource(BaseSource):
    @property
    def name(self) -> str:
        return "eastmoney"

    async def fetch(
        self, symbol: str, start_date: date, end_date: date
    ) -> pd.DataFrame:
        code = symbol.split(".")[1]
        start_str = start_date.strftime("%Y%m%d")
        end_str = end_date.strftime("%Y%m%d")

        raw = ak.stock_zh_a_hist(
            symbol=code, period="daily",
            start_date=start_str, end_date=end_str, adjust="",
        )
        if raw.empty:
            return pd.DataFrame()

        raw_qfq = ak.stock_zh_a_hist(
            symbol=code, period="daily",
            start_date=start_str, end_date=end_str, adjust="qfq",
        )
        raw_hfq = ak.stock_zh_a_hist(
            symbol=code, period="daily",
            start_date=start_str, end_date=end_str, adjust="hfq",
        )

        result = raw.rename(columns=COLUMN_MAP)
        result["date"] = pd.to_datetime(result["date"]).dt.date

        raw_qfq = raw_qfq.rename(columns=COLUMN_MAP)[["date", "close"]].rename(
            columns={"close": "close_qfq"}
        )
        raw_hfq = raw_hfq.rename(columns=COLUMN_MAP)[["date", "close"]].rename(
            columns={"close": "close_hfq"}
        )

        result = result.merge(raw_qfq, on="date", how="left")
        result = result.merge(raw_hfq, on="date", how="left")
        result["factor_qfq"] = (result["close_qfq"] / result["close"]).round(6)
        result["factor_hfq"] = (result["close_hfq"] / result["close"]).round(6)
        result.drop(columns=["close_qfq", "close_hfq"], inplace=True)

        return result[["date", "open", "high", "low", "close", "volume", "amount", "factor_qfq", "factor_hfq"]]
