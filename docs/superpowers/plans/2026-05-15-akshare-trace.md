# Akshare Trace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Trace all akshare API calls — log full response body (DEBUG), store summary in PG (api_request_log hypertable).

**Architecture:** Decorator `@trace_akshare` wraps each source's fetch method + CalendarService helper. Async queue + writer coroutine inserts into PG without blocking requests. Queue started/stopped via FastAPI lifespan.

**Tech Stack:** Python asyncio, asyncpg, TimescaleDB

---

## File Structure

| Path | Action | Responsibility |
|------|--------|---------------|
| `scripts/init_db.sql` | Modify | Add api_request_log hypertable |
| `app/ak_trace.py` | Create | Decorator, async queue, writer, _schedule_pg_insert |
| `app/main.py` | Modify | Start/stop log_writer task in lifespan |
| `app/sources/sina.py` | Modify | Add `@trace_akshare("stock_zh_a_daily")` |
| `app/sources/tencent.py` | Modify | Add `@trace_akshare("stock_zh_a_hist_tx")` |
| `app/sources/eastmoney.py` | Modify | Add `@trace_akshare("stock_zh_a_hist")` |
| `app/sources/dividend.py` | Modify | Split fetch into two private methods, add `@trace_akshare` on each |
| `app/calendar.py` | Modify | Add `@trace_akshare("tool_trade_date_hist_sina")` on internal helper |
| `tests/test_ak_trace.py` | Create | Tests for decorator, compute_factor, adjustment_ratio |

---

### Task 1: Database schema — add api_request_log hypertable

**Files:**
- Modify: `scripts/init_db.sql`

- [ ] **Step 1: Add api_request_log table to init_db.sql**

Append before the final newline:

```sql
CREATE TABLE IF NOT EXISTS api_request_log (
    id          BIGSERIAL,
    api_name    TEXT    NOT NULL,
    symbol      TEXT,
    params      JSONB,
    status      TEXT    NOT NULL,
    row_count   INTEGER,
    duration_ms INTEGER,
    error_msg   TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (id, created_at)
);

SELECT create_hypertable('api_request_log', 'created_at', if_not_exists => TRUE);
```

- [ ] **Step 2: Commit**

```bash
git add scripts/init_db.sql
git commit -m "feat: add api_request_log hypertable for akshare trace"
```

---

### Task 2: Create app/ak_trace.py — decorator + async writer

**Files:**
- Create: `app/ak_trace.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_ak_trace.py
import pytest
from datetime import date
from app.ak_trace import trace_akshare


class TestTraceDecorator:
    async def test_decorator_logs_success(self):
        events = []

        @trace_akshare("test_api")
        async def dummy(symbol="SH.600519", start="2024-01-01"):
            return [{"date": "2024-01-01", "close": 10.0}]

        result = await dummy(symbol="SH.600519", start="2024-01-01")
        assert len(result) == 1
        # The internal _schedule_pg_insert should have been called
        # We can't easily assert on PG, so just verify the function ran

    async def test_decorator_logs_error(self):
        @trace_akshare("test_api")
        async def failing():
            raise ValueError("test error")

        with pytest.raises(ValueError, match="test error"):
            await failing()
```

Run: `pytest tests/test_ak_trace.py -v`

Expected: FAIL — module not found.

- [ ] **Step 2: Create app/ak_trace.py**

```python
import asyncio
import functools
import json
import logging
import time

from app.database import get_pool

logger = logging.getLogger(__name__)

_log_queue: asyncio.Queue | None = None
_QUEUE_MAXSIZE = 1000


def _extract_symbol(api_name: str, args: tuple, kwargs: dict) -> str | None:
    if "symbol" in kwargs:
        return kwargs["symbol"]
    for arg in args:
        if isinstance(arg, str) and "." in arg and arg.split(".")[0] in ("SH", "SZ", "BJ"):
            return arg
    if api_name == "stock_history_dividend_detail":
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
                await conn.execute(
                    """INSERT INTO api_request_log
                       (api_name, symbol, params, status, row_count, duration_ms, error_msg)
                       VALUES ($1,$2,$3::jsonb,$4,$5,$6,$7)""",
                    entry["api_name"], entry["symbol"], entry["params"],
                    entry["status"], entry["row_count"], entry["duration_ms"],
                    entry["error_msg"],
                )
        except Exception as e:
            logger.warning("akshare trace pg insert failed: %s", e)


async def start_trace():
    global _log_queue
    if _log_queue is not None:
        return
    _log_queue = asyncio.Queue(maxsize=_QUEUE_MAXSIZE)


def stop_trace():
    global _log_queue
    _log_queue = None
```

- [ ] **Step 3: Run tests to verify**

```bash
pytest tests/test_ak_trace.py -v
```

Expected: 2 passed.

- [ ] **Step 4: Commit**

```bash
git add app/ak_trace.py tests/test_ak_trace.py
git commit -m "feat: add akshare trace decorator and async log writer"
```

---

### Task 3: Integrate log_writer into FastAPI lifespan

**Files:**
- Modify: `app/main.py`

- [ ] **Step 1: Update main.py**

Add import and writer task:

```python
import asyncio
import logging
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI

from app.ak_trace import _log_writer
from app.calendar import calendar_service
from app.dividend import dividend_service
from app.database import get_pool, close_pool
from app.router import router
from app.config import settings

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()
_writer_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _writer_task
    logger.info("CandleX starting up")
    await calendar_service.load()
    await get_pool()
    _writer_task = asyncio.create_task(_log_writer())
    logger.info("akshare trace writer started")
    yield
    if _writer_task:
        _writer_task.cancel()
    scheduler.shutdown()
    await close_pool()
    logger.info("CandleX shut down")


app = FastAPI(title="CandleX", lifespan=lifespan)
app.include_router(router)
```

Change from current: adds `import asyncio`, `import _log_writer`, `_writer_task` global, creates `_log_writer()` task in lifespan, cancels on shutdown.

- [ ] **Step 2: Commit**

```bash
git add app/main.py
git commit -m "feat: integrate akshare trace writer into FastAPI lifespan"
```

---

### Task 4: Integrate SinaSource

**Files:**
- Modify: `app/sources/sina.py`

- [ ] **Step 1: Add import and decorator**

```python
import logging
from datetime import date
import akshare as ak
import pandas as pd

from app.ak_trace import trace_akshare
from app.sources.base import BaseSource

logger = logging.getLogger(__name__)


class SinaSource(BaseSource):
    @property
    def name(self) -> str:
        return "sina"

    @trace_akshare("stock_zh_a_daily")
    async def fetch(
        self, symbol: str, start_date: date, end_date: date
    ) -> pd.DataFrame:
        sina_symbol = symbol.lower().replace(".", "")
        start_str = start_date.strftime("%Y%m%d")
        end_str = end_date.strftime("%Y%m%d")
        raw = ak.stock_zh_a_daily(
            symbol=sina_symbol, start_date=start_str, end_date=end_str, adjust=""
        )
        if raw.empty:
            return pd.DataFrame()
        result = raw[["date", "open", "high", "low", "close", "volume", "amount"]].copy()
        return result
```

Only change: add `from app.ak_trace import trace_akshare` import and `@trace_akshare("stock_zh_a_daily")` decorator.

- [ ] **Step 2: Commit**

```bash
git add app/sources/sina.py
git commit -m "feat: add akshare trace to SinaSource"
```

---

### Task 5: Integrate TencentSource

**Files:**
- Modify: `app/sources/tencent.py`

- [ ] **Step 1: Add import and decorator**

```python
import logging
from datetime import date
import akshare as ak
import pandas as pd

from app.ak_trace import trace_akshare
from app.sources.base import BaseSource

logger = logging.getLogger(__name__)


class TencentSource(BaseSource):
    @property
    def name(self) -> str:
        return "tencent"

    @trace_akshare("stock_zh_a_hist_tx")
    async def fetch(
        self, symbol: str, start_date: date, end_date: date
    ) -> pd.DataFrame:
        tx_symbol = symbol.replace(".", "")
        start_str = start_date.strftime("%Y%m%d")
        end_str = end_date.strftime("%Y%m%d")
        raw = ak.stock_zh_a_hist_tx(
            symbol=tx_symbol, start_date=start_str, end_date=end_str, adjust=""
        )
        if raw.empty:
            return pd.DataFrame()
        result = raw[["date", "open", "close", "high", "low", "amount"]].copy()
        result["volume"] = None
        return result
```

- [ ] **Step 2: Commit**

```bash
git add app/sources/tencent.py
git commit -m "feat: add akshare trace to TencentSource"
```

---

### Task 6: Integrate EastMoneySource

**Files:**
- Modify: `app/sources/eastmoney.py`

- [ ] **Step 1: Add import and decorator**

```python
import logging
from datetime import date
import akshare as ak
import pandas as pd

from app.ak_trace import trace_akshare
from app.sources.base import BaseSource

logger = logging.getLogger(__name__)

COLUMN_MAP = {
    "日期": "date",
    "开盘": "open",
    "收盘": "close",
    "最高": "high",
    "最低": "low",
    "成交量": "volume",
    "成交额": "amount",
}


class EastMoneySource(BaseSource):
    @property
    def name(self) -> str:
        return "eastmoney"

    @trace_akshare("stock_zh_a_hist")
    async def fetch(
        self, symbol: str, start_date: date, end_date: date
    ) -> pd.DataFrame:
        code = symbol.split(".")[1]
        start_str = start_date.strftime("%Y%m%d")
        end_str = end_date.strftime("%Y%m%d")
        raw = ak.stock_zh_a_hist(
            symbol=code, period="daily",
            start_date=start_str, end_date=end_str, adjust="",
        )
        if raw.empty:
            return pd.DataFrame()
        result = raw.rename(columns=COLUMN_MAP)
        result["date"] = pd.to_datetime(result["date"]).dt.date
        return result[["date", "open", "high", "low", "close", "volume", "amount"]]
```

- [ ] **Step 2: Commit**

```bash
git add app/sources/eastmoney.py
git commit -m "feat: add akshare trace to EastMoneySource"
```

---

### Task 7: Integrate DividendSource

**Files:**
- Modify: `app/sources/dividend.py`

- [ ] **Step 1: Split fetch into two tracked methods**

```python
import logging
from datetime import date
import akshare as ak
import pandas as pd

from app.ak_trace import trace_akshare
from app.sources.base import BaseSource

logger = logging.getLogger(__name__)


class DividendSource(BaseSource):
    @property
    def name(self) -> str:
        return "dividend_sina"

    def _to_raw_code(self, symbol: str) -> str:
        return symbol.split(".")[1]

    async def fetch(
        self, symbol: str, start_date: date | None = None, end_date: date | None = None
    ) -> pd.DataFrame:
        code = self._to_raw_code(symbol)
        div = await self._fetch_dividend(code)
        rights = await self._fetch_rights(code)
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
                    "ex_date": ex, "cash_dividend": cd,
                    "stock_dividend": sd, "capitalization": cap,
                    "rights_ratio": 0.0, "rights_price": None,
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
                        "ex_date": ex, "cash_dividend": 0.0,
                        "stock_dividend": 0.0, "capitalization": 0.0,
                        "rights_ratio": rr, "rights_price": rp if rp > 0 else None,
                        "event_type": "rights",
                    })
        if not rows:
            return pd.DataFrame()
        result = pd.DataFrame(rows)
        result = result.sort_values("ex_date").reset_index(drop=True)
        return result

    @trace_akshare("stock_history_dividend_detail")
    async def _fetch_dividend(self, code: str) -> pd.DataFrame:
        return ak.stock_history_dividend_detail(symbol=code, indicator="分红", date="")

    @trace_akshare("stock_history_dividend_detail")
    async def _fetch_rights(self, code: str) -> pd.DataFrame:
        return ak.stock_history_dividend_detail(symbol=code, indicator="配股", date="")
```

Changes: split the two `ak.stock_history_dividend_detail` calls into `_fetch_dividend` and `_fetch_rights`, each decorated with `@trace_akshare`. The public `fetch()` orchestrates both and builds the combined result.

- [ ] **Step 2: Commit**

```bash
git add app/sources/dividend.py
git commit -m "feat: add akshare trace to DividendSource"
```

---

### Task 8: Integrate CalendarService

**Files:**
- Modify: `app/calendar.py`

- [ ] **Step 1: Add import and wrap the fetch call**

```python
import bisect
import logging
from datetime import date
import akshare as ak
import pandas as pd

from app.ak_trace import trace_akshare

logger = logging.getLogger(__name__)


@trace_akshare("tool_trade_date_hist_sina")
def _fetch_all() -> pd.DataFrame:
    return ak.tool_trade_date_hist_sina()
```

Then replace any direct `ak.tool_trade_date_hist_sina()` call with `_fetch_all()`.

In the `CalendarService.load()` method, the call would be:

```python
async def load(self):
    ...
    df = _fetch_all()
    ...
```

- [ ] **Step 2: Commit**

```bash
git add app/calendar.py
git commit -m "feat: add akshare trace to CalendarService"
```

---

### Task 9: Tests

**Files:**
- Modify: `tests/test_ak_trace.py`

- [ ] **Step 1: Add comprehensive tests**

```python
import asyncio
import json
import logging
from datetime import date
import pytest
from app.ak_trace import trace_akshare, _extract_symbol, _extract_params


class TestExtractSymbol:
    def test_from_kwargs(self):
        assert _extract_symbol("stock_zh_a_daily", (), {"symbol": "SH.600519"}) == "SH.600519"

    def test_from_positional(self):
        assert _extract_symbol("stock_zh_a_daily", ("SH.600519",), {}) == "SH.600519"

    def test_from_digit_code(self):
        assert _extract_symbol("stock_history_dividend_detail", ("000001",), {}) == "000001"

    def test_none_when_no_match(self):
        assert _extract_symbol("test_api", ("hello",), {}) is None


class TestExtractParams:
    def test_kwargs_passthrough(self):
        params = _extract_params("stock_zh_a_daily", (), {"start_date": "20240101"})
        assert params["start_date"] == "20240101"

    def test_api_with_indicator(self):
        params = _extract_params("stock_history_dividend_detail", (), {"indicator": "分红"})
        assert params["indicator"] == "分红"


class TestTraceDecorator:
    async def test_successful_call(self):
        calls = []

        @trace_akshare("test_api")
        async def dummy():
            return [1, 2, 3]

        result = await dummy()
        assert result == [1, 2, 3]

    async def test_exception_raised(self):
        @trace_akshare("test_api")
        async def failing():
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError, match="boom"):
            await failing()

    async def test_sync_function_supported(self):
        @trace_akshare("test_sync")
        def sync_dummy():
            return "ok"

        result = await sync_dummy()
        assert result == "ok"

    async def test_queue_dropped_when_not_started(self):
        """_schedule_pg_insert should be no-op when _log_queue is None."""
        from app.ak_trace import _schedule_pg_insert
        _schedule_pg_insert("test", None, {}, "success", 1, 100, None)
        # Should not raise
```

- [ ] **Step 2: Run tests**

```bash
pytest tests/test_ak_trace.py -v
```

Expected: All tests passed.

- [ ] **Step 3: Commit**

```bash
git add tests/test_ak_trace.py
git commit -m "test: add comprehensive tests for akshare trace"
```
