import logging
from datetime import date
import akshare as ak
import pandas as pd

from app.sources.base import BaseSource

logger = logging.getLogger(__name__)


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

        logger.info("sina fetch raw %s [%s, %s]", sina_symbol, start_str, end_str)
        raw = ak.stock_zh_a_daily(
            symbol=sina_symbol, start_date=start_str, end_date=end_str, adjust=""
        )
        if raw.empty:
            logger.warning("sina raw data empty for %s", sina_symbol)
            return pd.DataFrame()
        logger.info("sina raw got %d rows for %s, index type=%s, index sample=%s",
                     len(raw), sina_symbol, type(raw.index), list(raw.index[:3]))

        logger.info("sina fetch qfq-factor %s", sina_symbol)
        factor_qfq = ak.stock_zh_a_daily(
            symbol=sina_symbol, start_date=start_str, end_date=end_str, adjust="qfq-factor"
        )
        logger.info("sina fetch hfq-factor %s", sina_symbol)
        factor_hfq = ak.stock_zh_a_daily(
            symbol=sina_symbol, start_date=start_str, end_date=end_str, adjust="hfq-factor"
        )

        logger.info("sina factor_qfq cols=%s shape=%s", list(factor_qfq.columns), factor_qfq.shape)
        logger.info("sina factor_hfq cols=%s shape=%s", list(factor_hfq.columns), factor_hfq.shape)

        result = raw[["open", "high", "low", "close", "volume", "amount"]].copy()
        result["date"] = raw.index
        result.reset_index(drop=True, inplace=True)
        logger.info("sina result date dtypes=%s sample=%s", result["date"].dtype, list(result["date"][:3]))

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
        result["factor_qfq"] = result.get("factor_qfq", pd.NA)
        result["factor_hfq"] = result.get("factor_hfq", pd.NA)
        result[["factor_qfq", "factor_hfq"]] = result[
            ["factor_qfq", "factor_hfq"]
        ].ffill()

        logger.info("sina returning %d rows, date dtype=%s sample=%s, factor_qfq sample=%s",
                     len(result), result["date"].dtype,
                     list(result["date"][:3]), list(result["factor_qfq"][:3]))
        return result
