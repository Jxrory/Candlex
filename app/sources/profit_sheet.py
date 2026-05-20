import logging

import akshare as ak
import pandas as pd

from app.ak_trace import trace_akshare

logger = logging.getLogger(__name__)


class ProfitSheetSource:
    @property
    def name(self) -> str:
        return "profit_sheet_em"

    def _to_raw_code(self, symbol: str) -> str:
        return symbol.replace(".", "")

    @trace_akshare("stock_profit_sheet_by_report_em")
    def _fetch(self, code: str) -> pd.DataFrame:
        return ak.stock_profit_sheet_by_report_em(symbol=code)

    async def fetch(self, symbol: str) -> pd.DataFrame:
        code = self._to_raw_code(symbol)
        logger.info("profit sheet source: fetching %s", code)
        df = await self._fetch(code)
        if df.empty:
            logger.warning("profit sheet source: empty result for %s", code)
            return pd.DataFrame()

        rows = []
        report_date_col = None
        for col in df.columns:
            if "report_date" in col.lower() or col in ("REPORT_DATE", "报告期", "截至日期", "截止日期"):
                report_date_col = col
                break

        if report_date_col is None:
            logger.error("profit sheet source: no date column found in %s", list(df.columns))
            return pd.DataFrame()

        for _, row in df.iterrows():
            rd = row[report_date_col]
            if pd.isna(rd):
                continue
            rd = pd.to_datetime(rd).date()

            row_dict = row.drop(report_date_col).to_dict()
            cleaned = {}
            for k, v in row_dict.items():
                try:
                    if isinstance(v, float) and (pd.isna(v) or pd.isnull(v)):
                        continue
                    if hasattr(v, "item"):
                        v = v.item()
                    cleaned[str(k)] = v
                except (ValueError, TypeError):
                    cleaned[str(k)] = str(v) if v is not None else None

            rows.append({"report_date": rd, "data": cleaned})

        if not rows:
            return pd.DataFrame()

        result = pd.DataFrame(rows)
        result = result.sort_values("report_date").reset_index(drop=True)
        logger.info("profit sheet source: returning %d records for %s", len(result), code)
        return result
