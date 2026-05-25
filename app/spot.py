import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import asyncpg
import pandas as pd

from app.sources.spot import SpotSource

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
        self, pool: asyncpg.Pool, symbol: str | None = None
    ) -> list[dict]:
        if symbol:
            query = """SELECT data FROM spot_snapshots
                       WHERE symbol = $1
                       ORDER BY snapshot_time DESC LIMIT 1"""
            async with pool.acquire() as conn:
                row = await conn.fetchrow(query, symbol)
            if not row:
                return []
            data = row["data"]
            if isinstance(data, str):
                data = json.loads(data)
            if isinstance(data, dict):
                return [data]
            return [dict(data)]

        query = """SELECT symbol, data FROM spot_snapshots
                   WHERE snapshot_time = (
                       SELECT MAX(snapshot_time) FROM spot_snapshots
                   ) ORDER BY symbol"""
        async with pool.acquire() as conn:
            rows = await conn.fetch(query)
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

    async def sync_all(self, pool: asyncpg.Pool) -> int:
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
                    volume_val = int(volume_val * 100)  # 手 → 股
            except (ValueError, TypeError):
                continue
            if close_val is not None and volume_val is not None:
                kline_rows.append((
                    symbol, snapshot_time.date(), open_val, high_val, low_val,
                    close_val, volume_val, amount_val, self.source.name,
                ))

        async with pool.acquire() as conn:
            await conn.executemany(
                """INSERT INTO spot_snapshots (symbol, snapshot_time, data, source)
                   VALUES ($1, $2, $3::jsonb, $4)
                   ON CONFLICT (symbol, snapshot_time) DO UPDATE SET
                       data = EXCLUDED.data,
                       source = EXCLUDED.source""",
                spot_rows,
            )

        if kline_rows:
            async with pool.acquire() as conn:
                await conn.executemany(
                    """INSERT INTO kline_data (symbol, date, open, high, low, close, volume, amount, source)
                       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                       ON CONFLICT (symbol, date) DO UPDATE SET
                           open = EXCLUDED.open,
                           high = EXCLUDED.high,
                           low = EXCLUDED.low,
                           close = EXCLUDED.close,
                           volume = EXCLUDED.volume,
                           amount = EXCLUDED.amount,
                           source = EXCLUDED.source""",
                    kline_rows,
                )

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
