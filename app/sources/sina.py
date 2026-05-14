from datetime import date
import akshare as ak
import pandas as pd

from app.sources.base import BaseSource


class SinaSource(BaseSource):
    @property
    def name(self) -> str:
        return "sina"

    async def fetch(
        self, symbol: str, start_date: date, end_date: date
    ) -> pd.DataFrame:
        sina_symbol = symbol.lower().replace(".", "")
        start_str = start_date.strftime("%Y%m%d")
        end_str = end_date.strftime("%Y%m%d")

        raw = ak.stock_zh_a_daily(
            symbol=sina_symbol, start_date=start_str, end_date=end_str, adjust=""
        )
        if raw.empty:
            return pd.DataFrame()

        factor_qfq = ak.stock_zh_a_daily(
            symbol=sina_symbol, start_date=start_str, end_date=end_str, adjust="qfq-factor"
        )
        factor_hfq = ak.stock_zh_a_daily(
            symbol=sina_symbol, start_date=start_str, end_date=end_str, adjust="hfq-factor"
        )

        result = raw[["open", "high", "low", "close", "volume", "amount"]].copy()
        result["date"] = raw.index
        result.reset_index(drop=True, inplace=True)

        factor_qfq["date"] = pd.to_datetime(factor_qfq["date"]).dt.date
        factor_hfq["date"] = pd.to_datetime(factor_hfq["date"]).dt.date

        result = result.merge(
            factor_qfq[["date", "qfq_factor"]], on="date", how="left"
        )
        result = result.merge(
            factor_hfq[["date", "hfq_factor"]], on="date", how="left"
        )
        result.rename(
            columns={"qfq_factor": "factor_qfq", "hfq_factor": "factor_hfq"},
            inplace=True,
        )
        result[["factor_qfq", "factor_hfq"]] = result[
            ["factor_qfq", "factor_hfq"]
        ].ffill()

        return result
