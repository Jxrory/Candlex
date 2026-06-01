import json
import logging
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.spot_repository import spot_repository
from src.repositories.kline_repository import kline_repository
from src.services.calendar_service import calendar_service
from src.tools.sources.spot import SpotSource

logger = logging.getLogger(__name__)


def _clean_spot_row(row: pd.Series) -> dict:
    result = {}
    for k, v in row.items():
        try:
            if isinstance(v, float) and (pd.isna(v) or pd.isnull(v)):
                continue
            if hasattr(v, "item"):
                v = v.item()
            result[str(k)] = v
        except (ValueError, TypeError):
            result[str(k)] = str(v) if v is not None else None
    return result


class SpotService:
    def __init__(self):
        self.source = SpotSource()
        self._code_col = "代码"

    async def fetch_real(self, symbol: str | None = None) -> list[dict]:
        df = await self.source.fetch_all()
        if symbol:
            df = self.source.filter_symbol(df, symbol)
        return df.to_dict(orient="records")

    async def get_latest(
        self, session: AsyncSession, symbol: str | None = None
    ) -> list[dict]:
        if symbol:
            data = await spot_repository.get_latest_by_symbol(session, symbol)
            if not data:
                return []
            return [data]

        rows = await spot_repository.get_all_latest(session)
        result = []
        for r in rows:
            data = r["data"]
            if isinstance(data, str):
                data = json.loads(data)
            entry = {"symbol": r["symbol"]}
            if isinstance(data, dict):
                entry.update(data)
            else:
                entry.update(dict(data))
            result.append(entry)
        return result

    async def sync_all(self, session: AsyncSession) -> int:
        await calendar_service.ensure_fresh(session)
        today = date.today()
        if not calendar_service.is_trading_day(today):
            logger.info("today %s is not a trading day, skipping spot sync", today)
            return 0

        df = await self.source.fetch_all()
        snapshot_time = datetime.now(tz=ZoneInfo("Asia/Shanghai"))

        spot_rows: list[tuple] = []
        kline_rows: list[tuple] = []
        for _, row in df.iterrows():
            data = _clean_spot_row(row)
            code = str(row.get(self._code_col, ""))
            symbol = _parse_sina_symbol(code)
            if not symbol:
                continue

            data_json = json.dumps(data, ensure_ascii=False, default=str)
            spot_rows.append((symbol, snapshot_time, data_json, self.source.name))

            try:
                open_val = _safe_float(row.get("今开"))
                high_val = _safe_float(row.get("最高"))
                low_val = _safe_float(row.get("最低"))
                close_val = _safe_float(row.get("最新价"))
                volume_val = _safe_float(row.get("成交量"))
                amount_val = _safe_float(row.get("成交额"))
                if volume_val is not None:
                    volume_val = int(volume_val * 100)
            except (ValueError, TypeError):
                continue
            if close_val is not None and volume_val is not None:
                kline_rows.append((
                    symbol, snapshot_time.date(), open_val, high_val, low_val,
                    close_val, volume_val, amount_val, self.source.name,
                ))

        await spot_repository.upsert_many(session, spot_rows)
        if kline_rows:
            await kline_repository.upsert_many(session, kline_rows)

        return len(spot_rows)


def _safe_float(val: object) -> float | None:
    if val is None:
        return None
    try:
        v = float(val)
        if pd.isna(v):
            return None
        return v
    except (ValueError, TypeError):
        return None


def _parse_sina_symbol(code: str) -> str | None:
    market_map = {"sh": "SH", "sz": "SZ", "bj": "BJ"}
    if len(code) >= 8:
        prefix = code[:2].lower()
        bare = code[2:]
        if prefix in market_map and bare.isdigit() and len(bare) == 6:
            return f"{market_map[prefix]}.{bare}"
    return None


spot_service = SpotService()
