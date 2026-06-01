import logging
from datetime import date
import akshare as ak
import pandas as pd

from src.services.ak_trace import trace_akshare
from src.tools.sources.base import BaseSource

logger = logging.getLogger(__name__)


class SinaSource(BaseSource):
    @property
    def name(self) -> str:
        return "sina"

    @trace_akshare("stock_zh_a_daily")
    async def fetch(
        self, symbol: str, start_date: date, end_date: date
    ) -> pd.DataFrame:
        sina_symbol = symbol.lower().replace(".", "")
        start_str = start_date.strftime("%Y%m%d")
        end_str = end_date.strftime("%Y%m%d")

        logger.info("sina fetch raw %s [%s, %s]", sina_symbol, start_str, end_str)
        raw = ak.stock_zh_a_daily(
            symbol=sina_symbol, start_date=start_str, end_date=end_str, adjust=""
        )
        if raw.empty:
            logger.warning("sina raw data empty for %s", sina_symbol)
            return pd.DataFrame()

        result = raw[["date", "open", "high", "low", "close", "volume", "amount"]].copy()

        logger.info("sina returning %d rows, date dtype=%s sample=%s",
                     len(result), result["date"].dtype, list(result["date"][:3]))
        return result
