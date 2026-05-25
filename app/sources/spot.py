import logging

import akshare as ak
import pandas as pd

from app.ak_trace import trace_akshare

logger = logging.getLogger(__name__)


class SpotSource:
    @property
    def name(self) -> str:
        return "eastmoney_spot"

    def _to_raw_code(self, symbol: str) -> str:
        return symbol.split(".")[1]

    @trace_akshare("stock_zh_a_spot_em")
    def _fetch_raw(self) -> pd.DataFrame:
        return ak.stock_zh_a_spot_em()

    async def fetch_all(self) -> pd.DataFrame:
        logger.info("spot source: fetching all")
        df = await self._fetch_raw()
        if df.empty:
            logger.warning("spot source: empty result")
        else:
            logger.info("spot source: returning %d records", len(df))
        return df

    def filter_symbol(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        code = self._to_raw_code(symbol)
        result = df[df["代码"] == code].copy()
        logger.info("spot source: filtered %s -> %d records", symbol, len(result))
        return result
