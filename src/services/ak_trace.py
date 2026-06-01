import asyncio
import functools
import json
import logging
import time

from src.database import get_pool
from src.repositories.api_log_repository import api_log_repository

logger = logging.getLogger(__name__)

_log_queue: asyncio.Queue | None = None
_QUEUE_MAXSIZE = 1000


def _extract_symbol(api_name: str, args: tuple, kwargs: dict) -> str | None:
    if "symbol" in kwargs:
        return kwargs["symbol"]
    for arg in args:
        if isinstance(arg, str) and "." in arg:
            parts = arg.split(".")
            if parts[0] in ("SH", "SZ", "BJ"):
                return arg
            if len(parts) == 2 and parts[1] in ("SH", "SZ", "BJ") and parts[0].isdigit() and len(parts[0]) == 6:
                return arg
    if api_name in ("stock_history_dividend_detail", "stock_news_em"):
        for arg in args:
            if isinstance(arg, str) and arg.isdigit() and len(arg) == 6:
                return arg
    return None


def _extract_params(api_name: str, args: tuple, kwargs: dict) -> dict:
    params = dict(kwargs)
    if api_name in ("stock_zh_a_daily", "stock_zh_a_hist_tx"):
        if len(args) >= 2:
            params["start_date"] = str(args[1])
        if len(args) >= 3:
            params["end_date"] = str(args[2])
    elif api_name == "stock_zh_a_hist":
        if len(args) >= 2:
            params["start_date"] = str(args[2]) if len(args) > 2 else None
        if len(args) >= 3:
            params["end_date"] = str(args[3]) if len(args) > 3 else None
    elif api_name == "stock_history_dividend_detail":
        if len(args) >= 1:
            params["symbol"] = str(args[0])
        params.setdefault("indicator", kwargs.get("indicator"))
    elif api_name == "stock_news_em":
        if "symbol" not in params and len(args) >= 1:
            params["symbol"] = str(args[-1])
    elif api_name == "stock_zh_a_spot":
        pass
    return params


def trace_akshare(api_name: str):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.monotonic()
            symbol = _extract_symbol(api_name, args, kwargs)
            params = _extract_params(api_name, args, kwargs)
            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                elapsed = int((time.monotonic() - start) * 1000)
                row_count = len(result) if hasattr(result, "__len__") else None

                logger.info(
                    "akshare %s symbol=%s params=%s status=success rows=%s duration=%sms",
                    api_name, symbol, params, row_count, elapsed,
                )
                logger.debug(
                    "akshare %s response_body=%s",
                    api_name,
                    result.to_json(orient="records") if hasattr(result, "to_json") else str(result)[:2000],
                )

                _schedule_pg_insert(api_name, symbol, params, "success", row_count, elapsed, None)
                return result
            except Exception as e:
                elapsed = int((time.monotonic() - start) * 1000)
                logger.error(
                    "akshare %s symbol=%s params=%s status=error error=%s duration=%sms",
                    api_name, symbol, params, e, elapsed,
                )
                _schedule_pg_insert(api_name, symbol, params, "error", None, elapsed, str(e))
                raise
        return wrapper
    return decorator


def _schedule_pg_insert(
    api_name: str, symbol: str | None, params: dict | None,
    status: str, row_count: int | None, duration_ms: int, error_msg: str | None,
) -> None:
    if _log_queue is None:
        return
    entry = {
        "api_name": api_name,
        "symbol": symbol,
        "params": json.dumps(params) if params else None,
        "status": status,
        "row_count": row_count,
        "duration_ms": duration_ms,
        "error_msg": error_msg,
    }
    try:
        _log_queue.put_nowait(entry)
    except asyncio.QueueFull:
        logger.warning("akshare trace queue full, dropping entry: %s", api_name)


async def _log_writer():
    global _log_queue
    _log_queue = asyncio.Queue(maxsize=_QUEUE_MAXSIZE)
    pool = await get_pool()
    while True:
        entry = await _log_queue.get()
        try:
            async with pool.acquire() as conn:
                await api_log_repository.insert(conn, entry)
        except Exception as e:
            logger.warning("akshare trace pg insert failed: %s", e)
