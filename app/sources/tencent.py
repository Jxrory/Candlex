from datetime import date
import akshare as ak
import pandas as pd

from app.sources.base import BaseSource


class TencentSource(BaseSource):
    @property
    def name(self) -> str:
        return "tencent"

    async def fetch(
        self, symbol: str, start_date: date, end_date: date
    ) -> pd.DataFrame:
        tx_symbol = symbol.replace(".", "")
        start_str = start_date.strftime("%Y%m%d")
        end_str = end_date.strftime("%Y%m%d")

        raw = ak.stock_zh_a_hist_tx(
            symbol=tx_symbol, start_date=start_str, end_date=end_str, adjust=""
        )
        if raw.empty:
            return pd.DataFrame()

        raw_qfq = ak.stock_zh_a_hist_tx(
            symbol=tx_symbol, start_date=start_str, end_date=end_str, adjust="qfq"
        )
        raw_hfq = ak.stock_zh_a_hist_tx(
            symbol=tx_symbol, start_date=start_str, end_date=end_str, adjust="hfq"
        )

        result = raw[["date", "open", "close", "high", "low", "amount"]].copy()
        result["volume"] = None

        raw_qfq = raw_qfq[["date", "close"]].rename(columns={"close": "close_qfq"})
        raw_hfq = raw_hfq[["date", "close"]].rename(columns={"close": "close_hfq"})

        result = result.merge(raw_qfq, on="date", how="left")
        result = result.merge(raw_hfq, on="date", how="left")
        result["factor_qfq"] = (result["close_qfq"] / result["close"]).round(6)
        result["factor_hfq"] = (result["close_hfq"] / result["close"]).round(6)
        result.drop(columns=["close_qfq", "close_hfq"], inplace=True)

        return result
