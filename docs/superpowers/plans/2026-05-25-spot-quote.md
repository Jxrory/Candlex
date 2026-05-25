# Spot Quote Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add real-time A-share spot quote endpoints (`/quote/spot/*`) with two modes — real-time (direct akshare, no cache) and post-market (DB-backed, populated by scheduled cron).

**Architecture:** Source → Service → DB/akshare, following existing `/balance/` pattern. 4 routes: `/quote/spot/real`, `/quote/spot/real/{symbol}`, `/quote/spot`, `/quote/spot/{symbol}`.

**Tech Stack:** FastAPI, asyncpg, akshare (stock_zh_a_spot_em), APScheduler

**Spec:** `docs/superpowers/specs/2026-05-25-spot-quote-design.md`

---

### Task 1: Add `spot_snapshots` DDL

**Files:**
- Modify: `scripts/init_db.sql`

- [ ] **Step 1: Append spot_snapshots table DDL**

Append to end of `scripts/init_db.sql`:

```sql
CREATE TABLE IF NOT EXISTS spot_snapshots (
    symbol         TEXT NOT NULL,
    snapshot_time  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    data           JSONB NOT NULL,
    source         TEXT NOT NULL,
    PRIMARY KEY (symbol, snapshot_time)
);

SELECT create_hypertable('spot_snapshots', 'snapshot_time', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_spot_snapshots_symbol_time ON spot_snapshots (symbol, snapshot_time DESC);
```

- [ ] **Step 2: Commit**

```bash
git add scripts/init_db.sql
git commit -m "feat: add spot_snapshots table DDL"
```

---

### Task 2: Create SpotSource

**Files:**
- Create: `app/sources/spot.py`
- Create: `tests/test_spot.py` (source tests only)

- [ ] **Step 1: Write the failing test for SpotSource**

Write to `tests/test_spot.py`:

```python
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock


@pytest.fixture
def mock_akshare():
    data = {
        "代码": ["600519", "000001"],
        "名称": ["贵州茅台", "平安银行"],
        "最新价": [1800.0, 12.5],
        "涨跌幅": [1.5, -0.3],
        "涨跌额": [27.0, -0.04],
        "成交量": [20000.0, 500000.0],
        "成交额": [3.6e7, 6.25e6],
        "最高": [1810.0, 12.6],
        "最低": [1790.0, 12.4],
        "今开": [1795.0, 12.5],
        "昨收": [1773.0, 12.54],
    }
    return pd.DataFrame(data)


def test_spot_source_name():
    from app.sources.spot import SpotSource
    source = SpotSource()
    assert source.name == "eastmoney_spot"


def test_spot_source_to_raw_code():
    from app.sources.spot import SpotSource
    source = SpotSource()
    assert source._to_raw_code("SH.600519") == "600519"
    assert source._to_raw_code("SZ.000001") == "000001"
    assert source._to_raw_code("BJ.830799") == "830799"


@pytest.mark.asyncio
async def test_spot_source_fetch_all(mock_akshare):
    from app.sources.spot import SpotSource
    source = SpotSource()
    with patch("akshare.stock_zh_a_spot_em", return_value=mock_akshare):
        df = await source.fetch_all()
        assert len(df) == 2
        assert list(df["代码"]) == ["600519", "000001"]


@pytest.mark.asyncio
async def test_spot_source_filter_symbol(mock_akshare):
    from app.sources.spot import SpotSource
    source = SpotSource()
    filtered = source.filter_symbol(mock_akshare, "SH.600519")
    assert len(filtered) == 1
    assert filtered.iloc[0]["代码"] == "600519"


def test_spot_source_filter_symbol_empty():
    from app.sources.spot import SpotSource
    source = SpotSource()
    df = source.filter_symbol(pd.DataFrame({"代码": ["000001"]}), "SH.600519")
    assert len(df) == 0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /opt/Code/Lab/CandleX && python -m pytest tests/test_spot.py::test_spot_source_name -v 2>&1
```

Expected: FAIL with ModuleNotFoundError or ImportError.

- [ ] **Step 3: Write minimal SpotSource implementation**

Write to `app/sources/spot.py`:

```python
import logging

import akshare as ak
import pandas as pd

from app.ak_trace import trace_akshare

logger = logging.getLogger(__name__)


class SpotSource:
    @property
    def name(self) -> str:
        return "eastmoney_spot"

    def _to_raw_code(self, symbol: str) -> str:
        return symbol.split(".")[1]

    @trace_akshare("stock_zh_a_spot_em")
    def _fetch_raw(self) -> pd.DataFrame:
        return ak.stock_zh_a_spot_em()

    async def fetch_all(self) -> pd.DataFrame:
        return await self._fetch_raw()

    def filter_symbol(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        code = self._to_raw_code(symbol)
        return df[df["代码"] == code].copy()
```

- [ ] **Step 4: Run source tests to verify they pass**

```bash
cd /opt/Code/Lab/CandleX && python -m pytest tests/test_spot.py -v 2>&1
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add app/sources/spot.py tests/test_spot.py
git commit -m "feat: add SpotSource for stock_zh_a_spot_em"
```

---

### Task 3: Add trace support for stock_zh_a_spot_em

**Files:**
- Modify: `app/ak_trace.py`

- [ ] **Step 1: Add stock_zh_a_spot_em case to `_extract_params`**

In `app/ak_trace.py`, before the `return params` at the end of `_extract_params`:

```python
    elif api_name == "stock_zh_a_spot_em":
        pass
```

- [ ] **Step 2: Verify existing trace tests still pass**

```bash
cd /opt/Code/Lab/CandleX && python -m pytest tests/test_ak_trace.py -v 2>&1
```

Expected: all passed.

- [ ] **Step 3: Commit**

```bash
git add app/ak_trace.py
git commit -m "feat: add stock_zh_a_spot_em trace support"
```

---

### Task 4: Create SpotService

**Files:**
- Create: `app/spot.py`
- Modify: `tests/test_spot.py` (add service tests)

- [ ] **Step 1: Write failing service tests**

Append to `tests/test_spot.py`:

```python
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import json
import pytest


class FakePool:
    """In-memory mock for asyncpg Pool used in post-market tests."""

    def __init__(self):
        self.rows = []

    def acquire(self):
        return _FakeAcquire(self)


class _FakeAcquire:
    def __init__(self, pool):
        self.pool = pool

    async def __aenter__(self):
        return _FakeConn(self.pool)

    async def __aexit__(self, *args):
        pass


class _FakeConn:
    def __init__(self, pool):
        self.pool = pool

    async def fetch(self, query, *params):
        return self.pool.rows

    async def fetchrow(self, query, *params):
        rows = [r for r in self.pool.rows if r.get("symbol") == params[0]] if params else self.pool.rows
        return rows[0] if rows else None

    async def executemany(self, query, rows):
        self.pool.rows = rows
        return len(rows)


@pytest.mark.asyncio
async def test_spot_service_fetch_real_all(mock_akshare):
    from app.spot import SpotService
    service = SpotService()
    with patch("akshare.stock_zh_a_spot_em", return_value=mock_akshare):
        result = await service.fetch_real()
    assert len(result) == 2
    assert result[0]["代码"] == "600519"


@pytest.mark.asyncio
async def test_spot_service_fetch_real_symbol(mock_akshare):
    from app.spot import SpotService
    service = SpotService()
    with patch("akshare.stock_zh_a_spot_em", return_value=mock_akshare):
        result = await service.fetch_real("SH.600519")
    assert len(result) == 1
    assert result[0]["代码"] == "600519"


@pytest.mark.asyncio
async def test_spot_service_get_latest_all():
    from app.spot import SpotService
    service = SpotService()
    pool = FakePool()
    pool.rows = [
        {"symbol": "SH.600519", "data": json.dumps({"代码": "600519", "最新价": 1800.0, "名称": "贵州茅台"})},
        {"symbol": "SZ.000001", "data": json.dumps({"代码": "000001", "最新价": 12.5, "名称": "平安银行"})},
    ]
    result = await service.get_latest(pool)
    assert len(result) == 2
    assert result[0]["symbol"] == "SH.600519"


@pytest.mark.asyncio
async def test_spot_service_get_latest_symbol():
    from app.spot import SpotService
    service = SpotService()
    pool = FakePool()
    pool.rows = [
        {"symbol": "SH.600519", "data": json.dumps({"代码": "600519", "最新价": 1800.0})},
    ]
    result = await service.get_latest(pool, "SH.600519")
    assert len(result) == 1
    assert result[0]["代码"] == "600519"


@pytest.mark.asyncio
async def test_spot_service_get_latest_no_data():
    from app.spot import SpotService
    service = SpotService()
    pool = FakePool()
    pool.rows = []
    result = await service.get_latest(pool)
    assert result == []


@pytest.mark.asyncio
async def test_spot_service_sync_all(mock_akshare):
    from app.spot import SpotService
    service = SpotService()
    pool = FakePool()
    with patch("akshare.stock_zh_a_spot_em", return_value=mock_akshare):
        with patch("app.spot.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 5, 25, 17, 0, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
            count = await service.sync_all(pool)
    assert count == 2
    assert len(pool.rows) == 2
    assert pool.rows[0][1] == "600519"  # symbol
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /opt/Code/Lab/CandleX && python -m pytest tests/test_spot.py -v 2>&1
```

Expected: some FAILED (module not found, function not defined).

- [ ] **Step 3: Write SpotService implementation**

Write to `app/spot.py`:

```python
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
            symbol = None
            for prefix in ("SH", "SZ", "BJ"):
                if _match_market(code, prefix):
                    symbol = f"{prefix}.{code}"
                    break
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


def _match_market(code: str, prefix: str) -> bool:
    if prefix == "SH":
        return code.startswith("6")
    elif prefix == "SZ":
        return code.startswith(("0", "3"))
    elif prefix == "BJ":
        return code.startswith(("4", "8"))
    return False
```

- [ ] **Step 4: Run all spot tests to verify they pass**

```bash
cd /opt/Code/Lab/CandleX && python -m pytest tests/test_spot.py -v 2>&1
```

Expected: 9 passed.

- [ ] **Step 5: Commit**

```bash
git add app/spot.py tests/test_spot.py
git commit -m "feat: add SpotService with real-time, DB, and kline sync"
```

---

### Task 5: Add routes to router

**Files:**
- Modify: `app/router.py`

- [ ] **Step 1: Write failing route tests**

Append to `tests/test_spot.py`:

```python
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_spot_real_route_all():
    with patch("app.spot.spot_service.fetch_real", return_value=[{"代码": "600519", "最新价": 1800.0}]):
        resp = client.get("/quote/spot/real")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["代码"] == "600519"


def test_spot_real_route_codes_filter():
    records = [
        {"代码": "600519", "最新价": 1800.0},
        {"代码": "000001", "最新价": 12.5},
    ]
    with patch("app.spot.spot_service.fetch_real", return_value=records):
        resp = client.get("/quote/spot/real?codes=600519")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["代码"] == "600519"


def test_spot_real_route_symbol():
    with patch("app.spot.spot_service.fetch_real", return_value=[{"代码": "600519", "最新价": 1800.0}]):
        resp = client.get("/quote/spot/real/SH.600519")
    assert resp.status_code == 200


def test_spot_real_route_invalid_symbol():
    resp = client.get("/quote/spot/real/INVALID")
    assert resp.status_code == 422


def test_spot_route_all():
    with patch("app.spot.spot_service.get_latest", return_value=[{"代码": "600519", "最新价": 1800.0}]):
        resp = client.get("/quote/spot")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1


def test_spot_route_symbol():
    with patch("app.spot.spot_service.get_latest", return_value=[{"代码": "600519", "最新价": 1800.0}]):
        resp = client.get("/quote/spot/SH.600519")
    assert resp.status_code == 200
```

- [ ] **Step 2: Run route tests to verify they fail**

```bash
cd /opt/Code/Lab/CandleX && python -m pytest tests/test_spot.py::test_spot_real_route_all -v 2>&1
```

Expected: FAIL with 404 or 405.

- [ ] **Step 3: Add routes and imports**

In `app/router.py`:

Add import at top:

```python
from app.spot import spot_service
```

Add routes (BEFORE `/quote/spot/{symbol}`):

```python
@router.get("/quote/spot/real", response_model=list[dict])
async def spot_real(
    codes: str | None = Query(None, description="comma-separated codes, e.g. 600519,000001"),
):
    logger.info("GET /quote/spot/real codes=%s", codes)
    records = await spot_service.fetch_real()
    if codes:
        code_set = set(c.strip() for c in codes.split(","))
        records = [r for r in records if str(r.get("代码", "")) in code_set]
    logger.info("GET /quote/spot/real returned %d records", len(records))
    return records


@router.get("/quote/spot/real/{symbol}")
async def spot_real_symbol(
    symbol: str = Path(pattern=r"^(SH|SZ|BJ)\.[0-9]{6}$"),
):
    logger.info("GET /quote/spot/real/%s", symbol)
    records = await spot_service.fetch_real(symbol)
    logger.info("GET /quote/spot/real/%s returned %d records", symbol, len(records))
    return records


@router.get("/quote/spot", response_model=list[dict])
async def spot():
    logger.info("GET /quote/spot")
    pool = await get_pool()
    records = await spot_service.get_latest(pool)
    logger.info("GET /quote/spot returned %d records", len(records))
    return records


@router.get("/quote/spot/{symbol}")
async def spot_symbol(
    symbol: str = Path(pattern=r"^(SH|SZ|BJ)\.[0-9]{6}$"),
):
    logger.info("GET /quote/spot/%s", symbol)
    pool = await get_pool()
    records = await spot_service.get_latest(pool, symbol)
    logger.info("GET /quote/spot/%s returned %d records", symbol, len(records))
    return records
```

- [ ] **Step 4: Run route tests to verify they pass**

```bash
cd /opt/Code/Lab/CandleX && python -m pytest tests/test_spot.py -v 2>&1
```

Expected: all 14 passed.

- [ ] **Step 5: Commit**

```bash
git add app/router.py tests/test_spot.py
git commit -m "feat: add /quote/spot/* routes"
```

---

### Task 6: Add scheduled cron job

**Files:**
- Modify: `app/main.py`

- [ ] **Step 1: Add import and cron function**

In `app/main.py`:

Add import at top:

```python
from app.spot import spot_service
```

Add function before `@asynccontextmanager`:

```python
async def sync_spot_snapshot():
    logger.info("scheduled task: sync spot snapshot")
    pool = await get_pool()
    try:
        count = await spot_service.sync_all(pool)
        logger.info("scheduled task: synced %d spot records", count)
    except Exception as e:
        logger.error("scheduled task: spot sync failed: %s", e)
```

Add job registration inside `lifespan`, after the stock list sync job:

```python
    scheduler.add_job(
        sync_spot_snapshot,
        trigger="cron",
        hour=17, minute=0,
        id="sync_spot_snapshot",
        replace_existing=True,
    )
```

Also add a startup run to immediately fetch if it had never been run:

```python
    asyncio.create_task(sync_spot_snapshot())
```

- [ ] **Step 2: Verify app starts**

```bash
cd /opt/Code/Lab/CandleX && python -c "from app.main import app; print('OK')" 2>&1
```

Expected: OK (possibly with some warnings, no errors).

- [ ] **Step 3: Commit**

```bash
git add app/main.py
git commit -m "feat: add spot snapshot cron at 17:00"
```

---

### Task 7: Run full test suite

- [ ] **Step 1: Run all tests**

```bash
cd /opt/Code/Lab/CandleX && python -m pytest -v 2>&1
```

Expected: all tests pass (existing + new spot tests).

- [ ] **Step 2: Final commit**

```bash
git add -A
git commit -m "chore: add real-time spot quote API"
```
