import logging

import akshare as ak
import pandas as pd

from app.ak_trace import trace_akshare

logger = logging.getLogger(__name__)


class NewsSource:
    @property
    def name(self) -> str:
        return "news_em"

    def _to_raw_code(self, symbol: str) -> str:
        return symbol.split(".")[1]

    @trace_akshare("stock_news_em")
    def _fetch(self, code: str) -> pd.DataFrame:
        return ak.stock_news_em(symbol=code)

    async def fetch(self, symbol: str) -> pd.DataFrame:
        code = self._to_raw_code(symbol)
        logger.info("news source: fetching %s", code)
        df = await self._fetch(code)
        if df.empty:
            logger.warning("news source: empty result for %s", code)
            return pd.DataFrame()

        rows = []
        for _, row in df.iterrows():
            publish_time = None
            if pd.notna(row.get("发布时间")):
                publish_time = pd.to_datetime(row["发布时间"]).to_pydatetime()

            rows.append({
                "symbol": symbol,
                "title": str(row.get("新闻标题", "")),
                "content": str(row.get("新闻内容", "")),
                "publish_time": publish_time,
                "source_name": str(row.get("文章来源")) if pd.notna(row.get("文章来源")) else None,
                "url": str(row.get("新闻链接", "")),
            })

        if not rows:
            return pd.DataFrame()

        result = pd.DataFrame(rows)
        result = result.sort_values("publish_time", ascending=False).reset_index(drop=True)
        logger.info("news source: returning %d records for %s", len(result), code)
        return result
