import asyncio
import logging
import re
from datetime import date
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

from src.tools.sources.base import BaseSource, BaseStockListSource

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=2)

_A_SHARE_RE = re.compile(r"^[036]\d{5}$")


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


def _exchange_for_code(code: str) -> str:
    first = code[0] if code else ""
    if first == "6":
        return "SH"
    if first in ("0", "3"):
        return "SZ"
    return "BJ"


class MootdxStockListSource(BaseStockListSource):
    @property
    def name(self) -> str:
        return "mootdx_stock_list"

    async def fetch(self, market: str) -> pd.DataFrame:
        if market != "ZH_A":
            logger.info("mootdx stock list: market %s not supported, returning empty", market)
            return pd.DataFrame()

        logger.info("mootdx stock list: fetching SH and SZ lists")

        def _fetch_sh() -> pd.DataFrame:
            from mootdx.quotes import Quotes
            from mootdx import consts
            client = Quotes.factory(market="std")
            return client.stocks(market=consts.MARKET_SH)

        def _fetch_sz() -> pd.DataFrame:
            from mootdx.quotes import Quotes
            from mootdx import consts
            client = Quotes.factory(market="std")
            return client.stocks(market=consts.MARKET_SZ)

        loop = asyncio.get_running_loop()
        sh_raw, sz_raw = await asyncio.gather(
            loop.run_in_executor(_executor, _fetch_sh),
            loop.run_in_executor(_executor, _fetch_sz),
        )

        def _process(raw: pd.DataFrame, exchange: str) -> list[dict]:
            rows = []
            for _, row in raw.iterrows():
                code = str(row["code"])
                if not _A_SHARE_RE.match(code):
                    continue
                rows.append({
                    "symbol": f"{exchange}.{code}",
                    "name": str(row["name"]).strip().replace("\x00", ""),
                    "market": "ZH_A",
                    "list_date": None,
                    "list_status": None,
                    "industry": None,
                    "sector": None,
                })
            return rows

        rows = []
        if sh_raw is not None and isinstance(sh_raw, pd.DataFrame) and not sh_raw.empty:
            rows.extend(_process(sh_raw, "SH"))
        if sz_raw is not None and isinstance(sz_raw, pd.DataFrame) and not sz_raw.empty:
            rows.extend(_process(sz_raw, "SZ"))

        result = pd.DataFrame(rows)
        logger.info("mootdx stock list: returning %d ZH_A stocks", len(result))
        return result
