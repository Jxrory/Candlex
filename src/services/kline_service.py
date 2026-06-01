import logging
from datetime import date, datetime, timedelta, timezone

import asyncpg
import pandas as pd

from src.config import settings
from src.repositories.kline_repository import kline_repository
from src.services.calendar_service import calendar_service
from src.services.dividend_service import dividend_service, compute_factor
from src.database import get_pool
from src.schemas.schemas import KlineRecord
from src.tools.sources.base import BaseSource
from src.tools.sources.sina import SinaSource
from src.tools.sources.tencent import TencentSource
from src.tools.sources.eastmoney import EastMoneySource
from src.tools.sources.mootdx import MootdxSource

logger = logging.getLogger(__name__)

SOURCES: dict[str, BaseSource] = {
    "sina": SinaSource(),
    "tencent": TencentSource(),
    "eastmoney": EastMoneySource(),
    "mootdx": MootdxSource(),
}


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

    async with pool.acquire() as conn:
        cached = await kline_repository.get_cached(conn, symbol, start, end)

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
                        rows = _df_to_rows(df, symbol, source_name)
                        async with pool.acquire() as conn:
                            await kline_repository.upsert_many(conn, rows)
                        break
                except Exception as e:
                    logger.error("%s %s failed: %s", symbol, source_name, e)
                    continue

            async with pool.acquire() as conn:
                cached = await kline_repository.get_cached(conn, symbol, start, end)
    else:
        for source_name in effective_priority:
            source = SOURCES.get(source_name)
            if not source:
                continue
            try:
                df = await source.fetch(symbol, start, end)
                if not df.empty:
                    rows = _df_to_rows(df, symbol, source_name)
                    async with pool.acquire() as conn:
                        await kline_repository.upsert_many(conn, rows)
                    break
            except Exception as e:
                logger.error("%s %s failed: %s", symbol, source_name, e)
                continue

        async with pool.acquire() as conn:
            cached = await kline_repository.get_cached(conn, symbol, start, end)

    records = _rows_to_records(cached)

    if adjust:
        async with pool.acquire() as conn:
            events = await dividend_service.get_events(conn, symbol)
            adj_map = await dividend_service.get_adj_ratios(conn, symbol)
        if events:
            records = _apply_adjust(records, events, adj_map, adjust)

    return records
