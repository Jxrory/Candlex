import logging
from datetime import date
import akshare as ak
import pandas as pd

from app.sources.base import BaseSource

logger = logging.getLogger(__name__)

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

        logger.info("eastmoney fetch raw %s [%s, %s]", code, start_str, end_str)
        raw = ak.stock_zh_a_hist(
            symbol=code, period="daily",
            start_date=start_str, end_date=end_str, adjust="",
        )
        if raw.empty:
            logger.warning("eastmoney raw data empty for %s", code)
            return pd.DataFrame()

        result = raw.rename(columns=COLUMN_MAP)
        result["date"] = pd.to_datetime(result["date"]).dt.date

        logger.info("eastmoney returning %d rows, date dtype=%s sample=%s",
                     len(result), result["date"].dtype, list(result["date"][:3]))
        return result[["date", "open", "high", "low", "close", "volume", "amount"]]
