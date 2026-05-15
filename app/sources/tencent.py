import logging
from datetime import date
import akshare as ak
import pandas as pd

from app.ak_trace import trace_akshare
from app.sources.base import BaseSource

logger = logging.getLogger(__name__)


class TencentSource(BaseSource):
    @property
    def name(self) -> str:
        return "tencent"

    @trace_akshare("stock_zh_a_hist_tx")
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

        result = raw[["date", "open", "close", "high", "low", "amount"]].copy()
        result["volume"] = None

        logger.info("tencent returning %d rows, date dtype=%s sample=%s",
                     len(result), result["date"].dtype, list(result["date"][:3]))
        return result
