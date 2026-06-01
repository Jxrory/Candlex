import logging
from datetime import date
import akshare as ak
import pandas as pd

from src.services.ak_trace import trace_akshare
from src.tools.sources.base import BaseSource

logger = logging.getLogger(__name__)


class DividendSource(BaseSource):
    @property
    def name(self) -> str:
        return "dividend_sina"

    def _to_raw_code(self, symbol: str) -> str:
        return symbol.split(".")[1]

    @trace_akshare("stock_history_dividend_detail")
    def _fetch_dividend(self, code: str) -> pd.DataFrame:
        return ak.stock_history_dividend_detail(symbol=code, indicator="分红", date="")

    @trace_akshare("stock_history_dividend_detail")
    def _fetch_rights(self, code: str) -> pd.DataFrame:
        return ak.stock_history_dividend_detail(symbol=code, indicator="配股", date="")

    async def fetch(
        self, symbol: str, start_date: date | None = None, end_date: date | None = None
    ) -> pd.DataFrame:
        code = self._to_raw_code(symbol)

        logger.info("dividend source fetch dividend %s", code)
        try:
            div = await self._fetch_dividend(code)
        except Exception as e:
            logger.error("dividend fetch failed for %s: %s", code, e)
            return pd.DataFrame()

        logger.info("dividend source fetch rights %s", code)
        try:
            rights = await self._fetch_rights(code)
        except Exception as e:
            logger.error("rights fetch failed for %s: %s", code, e)
            rights = pd.DataFrame()

        rows = []
        if not div.empty:
            div = div[div["进度"] == "实施"].copy()
            div = div[div["除权除息日"].notna()].copy()
            for _, r in div.iterrows():
                sd = float(r.get("送股", 0) or 0) / 10
                cap = float(r.get("转增", 0) or 0) / 10
                cd = float(r.get("派息", 0) or 0) / 10
                ex = r["除权除息日"]
                if hasattr(ex, "date"):
                    ex = ex.date()
                rows.append({
                    "ex_date": ex,
                    "cash_dividend": cd,
                    "stock_dividend": sd,
                    "capitalization": cap,
                    "rights_ratio": 0.0,
                    "rights_price": None,
                    "event_type": "dividend",
                })

        if not rights.empty:
            for _, r in rights.iterrows():
                rr = float(r.get("配股方案", 0) or 0) / 10
                rp = float(r.get("配股价格", 0) or 0)
                ex = r.get("除权日")
                if pd.isna(ex):
                    continue
                if hasattr(ex, "date"):
                    ex = ex.date()

                merged = False
                for existing in rows:
                    if existing["ex_date"] == ex:
                        existing["rights_ratio"] = rr
                        existing["rights_price"] = rp
                        existing["event_type"] = "combined"
                        merged = True
                        break
                if not merged:
                    rows.append({
                        "ex_date": ex,
                        "cash_dividend": 0.0,
                        "stock_dividend": 0.0,
                        "capitalization": 0.0,
                        "rights_ratio": rr,
                        "rights_price": rp if rp > 0 else None,
                        "event_type": "rights",
                    })

        if not rows:
            return pd.DataFrame()

        result = pd.DataFrame(rows)
        result = result.sort_values("ex_date").reset_index(drop=True)
        logger.info("dividend source returning %d events for %s", len(result), code)
        return result
