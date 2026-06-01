import asyncio
import logging
from datetime import date
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

from src.tools.sources.base import BaseSource

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=2)


class MootdxDividendSource(BaseSource):
    @property
    def name(self) -> str:
        return "mootdx_dividend"

    def _to_raw_code(self, symbol: str) -> str:
        return symbol.split(".")[1]

    async def fetch(
        self, symbol: str, start_date: date | None = None, end_date: date | None = None
    ) -> pd.DataFrame:
        code = self._to_raw_code(symbol)

        logger.info("mootdx dividend fetch %s", code)

        def _fetch() -> pd.DataFrame:
            from mootdx.quotes import Quotes
            client = Quotes.factory(market="std")
            raw = client.xdxr(symbol=code)
            if raw is None or raw.empty:
                return pd.DataFrame()
            return raw[raw["category"] == 1].copy()

        loop = asyncio.get_running_loop()
        raw = await loop.run_in_executor(_executor, _fetch)

        if raw.empty:
            return raw

        rows = []
        for _, r in raw.iterrows():
            cd = float(r.get("fenhong", 0) or 0) / 10
            sz = float(r.get("songzhuangu", 0) or 0) / 10
            rr = float(r.get("peigu", 0) or 0) / 10
            rp = float(r.get("peigujia", 0) or 0)

            if cd == 0 and sz == 0 and rr == 0:
                continue

            ex_date = date(int(r["year"]), int(r["month"]), int(r["day"]))

            has_div = cd > 0 or sz > 0
            has_rights = rr > 0

            if has_div and has_rights:
                event_type = "combined"
            elif has_div:
                event_type = "dividend"
            else:
                event_type = "rights"

            rows.append({
                "ex_date": ex_date,
                "cash_dividend": cd,
                "stock_dividend": sz,
                "capitalization": 0.0,
                "rights_ratio": rr,
                "rights_price": rp if rp > 0 else None,
                "event_type": event_type,
            })

        result = pd.DataFrame(rows)
        result = result.sort_values("ex_date").reset_index(drop=True)

        if start_date:
            result = result[result["ex_date"] >= start_date]
        if end_date:
            result = result[result["ex_date"] <= end_date]

        logger.info("mootdx dividend returning %d events for %s", len(result), code)
        return result
