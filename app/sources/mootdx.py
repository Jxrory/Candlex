import asyncio
import logging
from datetime import date
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

from app.sources.base import BaseSource

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=2)


class MootdxSource(BaseSource):
    @property
    def name(self) -> str:
        return "mootdx"

    async def fetch(
        self, symbol: str, start_date: date, end_date: date
    ) -> pd.DataFrame:
        code = symbol.split(".")[1]
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")

        logger.info("mootdx fetch raw %s [%s, %s]", code, start_str, end_str)

        def _fetch() -> pd.DataFrame:
            from mootdx.quotes import Quotes
            client = Quotes.factory(market="std")
            return client.k(symbol=code, begin=start_str, end=end_str)

        loop = asyncio.get_running_loop()
        raw = await loop.run_in_executor(_executor, _fetch)

        if raw is None or (isinstance(raw, pd.DataFrame) and raw.empty):
            logger.warning("mootdx raw data empty for %s", code)
            return pd.DataFrame()

        result = raw[["date", "open", "high", "low", "close", "vol", "amount"]].copy()
        result["volume"] = result["vol"] * 100
        result.drop(columns=["vol"], inplace=True)
        result["date"] = pd.to_datetime(result["date"])

        logger.info("mootdx returning %d rows", len(result))
        return result[["date", "open", "high", "low", "close", "volume", "amount"]]
