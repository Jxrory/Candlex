import logging
import akshare as ak
import pandas as pd

from src.services.ak_trace import trace_akshare
from src.tools.sources.base import BaseStockListSource

logger = logging.getLogger(__name__)


def _code_to_exchange(code: str) -> str:
    first_char = code[0] if code else ""
    if first_char == "6":
        return "SH"
    elif first_char in ("0", "3"):
        return "SZ"
    return "BJ"


class StockListSource(BaseStockListSource):
    @property
    def name(self) -> str:
        return "stock_list"

    @trace_akshare("stock_info_a_code_name")
    def _fetch_a_code_name(self) -> pd.DataFrame:
        return ak.stock_info_a_code_name()

    async def fetch(self, market: str) -> pd.DataFrame:
        if market != "ZH_A":
            logger.info("stock list source: market %s not implemented, returning empty", market)
            return pd.DataFrame()

        logger.info("stock list source: fetching A-share list")
        df = await self._fetch_a_code_name()
        if df.empty:
            return pd.DataFrame()

        rows = []
        for _, row in df.iterrows():
            code = str(row["code"])
            name = str(row["name"])
            exchange = _code_to_exchange(code)
            rows.append({
                "symbol": f"{exchange}.{code}",
                "name": name,
                "market": "ZH_A",
                "list_date": None,
                "list_status": None,
                "industry": None,
                "sector": None,
            })

        result = pd.DataFrame(rows)
        logger.info("stock list source: returning %d ZH_A stocks", len(result))
        return result
