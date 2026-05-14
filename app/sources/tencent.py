import logging
from datetime import date
import akshare as ak
import pandas as pd

from app.sources.base import BaseSource

logger = logging.getLogger(__name__)


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

        logger.info("tencent fetch raw %s [%s, %s]", tx_symbol, start_str, end_str)
        raw = ak.stock_zh_a_hist_tx(
            symbol=tx_symbol, start_date=start_str, end_date=end_str, adjust=""
        )
        if raw.empty:
            logger.warning("tencent raw data empty for %s", tx_symbol)
            return pd.DataFrame()
        logger.info("tencent raw got %d rows for %s, date dtype=%s sample=%s",
                     len(raw), tx_symbol, raw["date"].dtype, list(raw["date"][:3]))

        logger.info("tencent fetch qfq %s", tx_symbol)
        raw_qfq = ak.stock_zh_a_hist_tx(
            symbol=tx_symbol, start_date=start_str, end_date=end_str, adjust="qfq"
        )
        logger.info("tencent fetch hfq %s", tx_symbol)
        raw_hfq = ak.stock_zh_a_hist_tx(
            symbol=tx_symbol, start_date=start_str, end_date=end_str, adjust="hfq"
        )

        result = raw[["date", "open", "close", "high", "low", "amount"]].copy()
        result["volume"] = None

        raw_qfq = raw_qfq[["date", "close"]].rename(columns={"close": "close_qfq"})
        raw_hfq = raw_hfq[["date", "close"]].rename(columns={"close": "close_hfq"})

        result = result.merge(raw_qfq, on="date", how="left")
        result = result.merge(raw_hfq, on="date", how="left")
        result["factor_qfq"] = (result["close_qfq"] / result["close"]).round(6).fillna(1.0)
        result["factor_hfq"] = (result["close_hfq"] / result["close"]).round(6).fillna(1.0)
        result.drop(columns=["close_qfq", "close_hfq"], inplace=True)

        logger.info("tencent returning %d rows, date dtype=%s sample=%s",
                     len(result), result["date"].dtype, list(result["date"][:3]))
        return result
