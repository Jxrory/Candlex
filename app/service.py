import logging
from datetime import date, datetime, timedelta, timezone

import asyncpg
import pandas as pd

from app.config import settings
from app.calendar import calendar_service
from app.dividend import dividend_service, compute_factor
from app.database import get_pool
from app.schemas import KlineRecord
from app.sources.base import BaseSource
from app.sources.sina import SinaSource
from app.sources.tencent import TencentSource
from app.sources.eastmoney import EastMoneySource

logger = logging.getLogger(__name__)

SOURCES: dict[str, BaseSource] = {
    "sina": SinaSource(),
    "tencent": TencentSource(),
    "eastmoney": EastMoneySource(),
}


async def query_cached(
    pool: asyncpg.Pool, symbol: str, start: date, end: date
) -> list[asyncpg.Record]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT date, open, high, low, close, volume, amount
               FROM kline_data
               WHERE symbol = $1 AND date BETWEEN $2 AND $3
               ORDER BY date""",
            symbol, start, end,
        )
    return rows


def _to_date(val) -> date:
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    if isinstance(val, pd.Timestamp):
        return val.date()
    return pd.Timestamp(val).date()


def _df_to_rows(df: pd.DataFrame, symbol: str, source: str) -> list[tuple]:
    rows: list[tuple] = []
    for _, row in df.iterrows():
        rows.append((
            symbol,
            _to_date(row["date"]),
            float(row["open"]) if pd.notna(row.get("open")) else None,
            float(row["high"]) if pd.notna(row.get("high")) else None,
            float(row["low"]) if pd.notna(row.get("low")) else None,
            float(row["close"]) if pd.notna(row.get("close")) else None,
            int(row["volume"]) if pd.notna(row.get("volume")) else None,
            float(row["amount"]) if pd.notna(row.get("amount")) else None,
            source,
        ))
    return rows


async def upsert_kline(
    pool: asyncpg.Pool, symbol: str, df: pd.DataFrame, source: str
) -> None:
    if df.empty:
        return
    rows = _df_to_rows(df, symbol, source)
    async with pool.acquire() as conn:
        await conn.executemany(
            """INSERT INTO kline_data
               (symbol, date, open, high, low, close, volume, amount, source)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
               ON CONFLICT (symbol, date)
               DO UPDATE SET
                   open=EXCLUDED.open, high=EXCLUDED.high,
                   low=EXCLUDED.low, close=EXCLUDED.close,
                   volume=EXCLUDED.volume, amount=EXCLUDED.amount,
                   source=EXCLUDED.source""",
            rows,
        )


def _rows_to_records(rows: list[asyncpg.Record]) -> list[KlineRecord]:
    return [
        KlineRecord(
            date=r["date"],
            open=float(r["open"]) if r["open"] is not None else 0.0,
            high=float(r["high"]) if r["high"] is not None else 0.0,
            low=float(r["low"]) if r["low"] is not None else 0.0,
            close=float(r["close"]) if r["close"] is not None else 0.0,
            volume=int(r["volume"]) if r["volume"] is not None else None,
            amount=float(r["amount"]) if r["amount"] is not None else None,
        )
        for r in rows
    ]


def _apply_adjust(
    records: list[KlineRecord], events: list, adj_map: dict[date, float], adjust: str
) -> list[KlineRecord]:
    pairs = [(e.ex_date, adj_map.get(e.ex_date, 1.0)) for e in events]
    adjusted: list[KlineRecord] = []
    for r in records:
        factor = compute_factor(pairs, r.date, adjust)
        if factor and factor != 1.0:
            adjusted.append(r.model_copy(update={
                "open": round(r.open * factor, 3),
                "high": round(r.high * factor, 3),
                "low": round(r.low * factor, 3),
                "close": round(r.close * factor, 3),
            }))
        else:
            adjusted.append(r)
    return adjusted


async def get_kline(
    symbol: str,
    start: date,
    end: date,
    adjust: str | None = None,
    source: str | None = None,
) -> list[KlineRecord]:
    pool = await get_pool()
    today = date.today()

    await calendar_service.ensure_fresh()
    start = calendar_service.nearest_forward(start)
    end = calendar_service.nearest_backward(end)

    effective_priority = list(settings.source_priority)
    if source:
        if source in effective_priority:
            effective_priority.remove(source)
        effective_priority.insert(0, source)

    cached = await query_cached(pool, symbol, start, end)

    if cached:
        cached_dates = [r["date"] for r in cached]
        min_cached = min(cached_dates)
        max_cached = max(cached_dates)

        needs_fetch = False
        fetch_from = start

        if start < min_cached:
            needs_fetch = True
            fetch_from = start
        if end > max_cached:
            needs_fetch = True
            fetch_from = min(fetch_from, start)

        if needs_fetch:
            for source_name in effective_priority:
                source = SOURCES.get(source_name)
                if not source:
                    continue
                try:
                    df = await source.fetch(symbol, fetch_from, end)
                    if not df.empty:
                        await upsert_kline(pool, symbol, df, source_name)
                        break
                except Exception as e:
                    logger.error("%s %s failed: %s", symbol, source_name, e)
                    continue

            cached = await query_cached(pool, symbol, start, end)
    else:
        for source_name in effective_priority:
            source = SOURCES.get(source_name)
            if not source:
                continue
            try:
                df = await source.fetch(symbol, start, end)
                if not df.empty:
                    await upsert_kline(pool, symbol, df, source_name)
                    break
            except Exception as e:
                logger.error("%s %s failed: %s", symbol, source_name, e)
                continue

        cached = await query_cached(pool, symbol, start, end)

    records = _rows_to_records(cached)

    if adjust:
        events = await dividend_service.get_events(pool, symbol)
        adj_map = await dividend_service.get_adj_ratios(pool, symbol)
        if events:
            records = _apply_adjust(records, events, adj_map, adjust)

    return records
