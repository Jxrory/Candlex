# Stock List Service Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a stock list caching endpoint with monthly sync for Chinese A-shares.

**Architecture:** New `StockListSource` calls `ak.stock_info_a_code_name()` for ZH_A data; `StockListService` handles DB upsert/query; new `GET /stocks` route returns from DB (cached) or re-fetches on `refresh=true`.

**Tech Stack:** FastAPI, asyncpg, akshare, APScheduler

---

### Task 1: Add DB schema for stock_info table

**Files:**
- Modify: `scripts/init_db.sql`

- [ ] **Step 1: Add stock_info table creation**

Insert the table definition **after the api_request_log block** in `scripts/init_db.sql`:

```sql
CREATE TABLE IF NOT EXISTS stock_info (
    symbol       TEXT    NOT NULL PRIMARY KEY,
    name         TEXT    NOT NULL,
    market       TEXT    NOT NULL,
    list_date    DATE,
    list_status  TEXT,
    industry     TEXT,
    sector       TEXT,
    updated_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_stock_info_market ON stock_info (market);
```

- [ ] **Step 2: Verify the SQL**

Run: `cat scripts/init_db.sql` and check no syntax issues.

- [ ] **Step 3: Commit**

```bash
git add scripts/init_db.sql
git commit -m "feat: add stock_info table schema"
```

---

### Task 2: Add StockInfoRecord Pydantic model

**Files:**
- Modify: `app/schemas.py`

- [ ] **Step 1: Add StockInfoRecord to schemas.py**

Append after `DividendRecord` class in `app/schemas.py`:

```python
class StockInfoRecord(BaseModel):
    symbol: str
    name: str
    market: str
    list_date: date | None = None
    list_status: str | None = None
    industry: str | None = None
    sector: str | None = None
```

- [ ] **Step 2: Verify import works**

Run: `python -c "from app.schemas import StockInfoRecord; print(StockInfoRecord(symbol='SH.600519', name='茅台', market='ZH_A'))"`

- [ ] **Step 3: Commit**

```bash
git add app/schemas.py
git commit -m "feat: add StockInfoRecord schema"
```

---

### Task 3: Create StockListSource

**Files:**
- Create: `app/sources/stock_list.py`

- [ ] **Step 1: Write StockListSource**

```python
import logging
from datetime import date
import akshare as ak
import pandas as pd

from app.ak_trace import trace_akshare

logger = logging.getLogger(__name__)


def _code_to_exchange(code: str) -> str:
    prefix = code[:3]
    if prefix.startswith("6"):
        return "SH"
    elif prefix.startswith("0") or prefix.startswith("3"):
        return "SZ"
    return "BJ"


class StockListSource:
    @property
    def name(self) -> str:
        return "stock_list"

    @trace_akshare("stock_info_a_code_name")
    def _fetch_a_code_name(self) -> pd.DataFrame:
        return ak.stock_info_a_code_name()

    async def fetch(self, market: str) -> pd.DataFrame:
        if market != "ZH_A":
            logger.info("stock list source: market %s not implemented, returning empty", market)
            return pd.DataFrame()

        logger.info("stock list source: fetching A-share list")
        df = self._fetch_a_code_name()
        if df.empty:
            return pd.DataFrame()

        rows = []
        for _, row in df.iterrows():
            code = str(row["code"])
            name = str(row["name"])
            exchange = _code_to_exchange(code)
            market_value = "ZH_A"
            rows.append({
                "symbol": f"{exchange}.{code}",
                "name": name,
                "market": market_value,
                "list_date": None,
                "list_status": None,
                "industry": None,
                "sector": None,
            })

        result = pd.DataFrame(rows)
        logger.info("stock list source: returning %d ZH_A stocks", len(result))
        return result
```

- [ ] **Step 2: Verify imports**

Run: `python -c "from app.sources.stock_list import StockListSource, _code_to_exchange; print(_code_to_exchange('600519')); print(_code_to_exchange('000001')); print(_code_to_exchange('300750')); print(_code_to_exchange('830799'))"`

Expected output:
```
SH
SZ
SZ
BJ
```

- [ ] **Step 3: Commit**

```bash
git add app/sources/stock_list.py
git commit -m "feat: add StockListSource for A-share stock list"
```

---

### Task 4: Create StockListService

**Files:**
- Create: `app/stock_list.py`

- [ ] **Step 1: Write StockListService**

```python
import logging
from datetime import date
import asyncpg
import pandas as pd

from app.database import get_pool
from app.schemas import StockInfoRecord
from app.sources.stock_list import StockListSource

logger = logging.getLogger(__name__)


class StockListService:
    def __init__(self):
        self.source = StockListSource()

    async def get_stocks(
        self, pool: asyncpg.Pool, market: str | None = None
    ) -> list[StockInfoRecord]:
        if market:
            query = "SELECT symbol, name, market, list_date, list_status, industry, sector FROM stock_info WHERE market = $1 ORDER BY symbol"
            params = [market]
        else:
            query = "SELECT symbol, name, market, list_date, list_status, industry, sector FROM stock_info ORDER BY symbol"
            params = []

        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        return [
            StockInfoRecord(
                symbol=r["symbol"],
                name=r["name"],
                market=r["market"],
                list_date=r["list_date"],
                list_status=r["list_status"],
                industry=r["industry"],
                sector=r["sector"],
            )
            for r in rows
        ]

    async def sync(self, pool: asyncpg.Pool, market: str) -> int:
        df = await self.source.fetch(market)
        if df.empty:
            return 0

        rows: list[tuple] = []
        for _, row in df.iterrows():
            rows.append((
                row["symbol"],
                row["name"],
                row["market"],
                row.get("list_date"),
                row.get("list_status"),
                row.get("industry"),
                row.get("sector"),
            ))

        async with pool.acquire() as conn:
            await conn.executemany(
                """INSERT INTO stock_info (symbol, name, market, list_date, list_status, industry, sector)
                   VALUES ($1,$2,$3,$4,$5,$6,$7)
                   ON CONFLICT (symbol) DO UPDATE SET
                       name = EXCLUDED.name,
                       list_date = COALESCE(EXCLUDED.list_date, stock_info.list_date),
                       list_status = COALESCE(EXCLUDED.list_status, stock_info.list_status),
                       industry = COALESCE(EXCLUDED.industry, stock_info.industry),
                       sector = COALESCE(EXCLUDED.sector, stock_info.sector),
                       updated_at = NOW()""",
                rows,
            )
        return len(rows)


stock_list_service = StockListService()
```

- [ ] **Step 2: Verify imports**

Run: `python -c "from app.stock_list import stock_list_service, StockListService; print(type(stock_list_service))"`

- [ ] **Step 3: Commit**

```bash
git add app/stock_list.py
git commit -m "feat: add StockListService"
```

---

### Task 5: Add /stocks route

**Files:**
- Modify: `app/router.py`

- [ ] **Step 1: Add import and route**

At the top of `app/router.py`, add import:
```python
from app.stock_list import stock_list_service
from app.schemas import StockInfoRecord
```

Then add the route before or after existing routes:
```python
@router.get("/stocks", response_model=list[StockInfoRecord])
async def stocks(
    market: str | None = Query(None),
    refresh: bool = Query(False),
):
    logger.info("GET /stocks market=%s refresh=%s", market, refresh)
    pool = await get_pool()
    if refresh:
        market_to_sync = market or "ZH_A"
        count = await stock_list_service.sync(pool, market_to_sync)
        logger.info("GET /stocks sync completed: %d records for %s", count, market_to_sync)
    records = await stock_list_service.get_stocks(pool, market)
    logger.info("GET /stocks returned %d records", len(records))
    return records
```

- [ ] **Step 2: Verify no import duplication**

Check that `StockInfoRecord` isn't imported twice (it's already imported by kline route potentially).

- [ ] **Step 3: Commit**

```bash
git add app/router.py
git commit -m "feat: add GET /stocks endpoint"
```

---

### Task 6: Enable scheduler for stock list monthly sync

**Files:**
- Modify: `app/main.py`

- [ ] **Step 1: Add import and sync function**

Add import at top:
```python
from app.stock_list import stock_list_service
```

Add a new sync function after `sync_all_dividends`:
```python
async def sync_stock_list():
    logger.info("scheduled task: sync stock list")
    pool = await get_pool()
    try:
        count = await stock_list_service.sync(pool, "ZH_A")
        logger.info("scheduled task: synced %d stock records", count)
    except Exception as e:
        logger.error("scheduled task: stock list sync failed: %s", e)
```

- [ ] **Step 2: Register the job in lifespan**

Inside the `lifespan` context manager, after `get_pool()`, add:
```python
    scheduler.add_job(
        sync_stock_list,
        trigger="cron",
        day=15,
        hour=8,
        minute=30,
        id="sync_stock_list",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("scheduler started, stock list sync at 08:30 on day 15")
```

- [ ] **Step 3: Add scheduler.shutdown() on exit**

In the yield/cleanup section, uncomment `scheduler.shutdown()` or add if not present:
```python
    scheduler.shutdown()
```

- [ ] **Step 4: Commit**

```bash
git add app/main.py
git commit -m "feat: add monthly stock list sync scheduler"
```

---

### Task 7: Write tests

**Files:**
- Create: `tests/test_stock_list.py`

- [ ] **Step 1: Write StockListSource unit tests**

```python
from app.sources.stock_list import _code_to_exchange


def test_code_to_exchange_sh():
    assert _code_to_exchange("600519") == "SH"
    assert _code_to_exchange("601857") == "SH"
    assert _code_to_exchange("688981") == "SH"


def test_code_to_exchange_sz():
    assert _code_to_exchange("000001") == "SZ"
    assert _code_to_exchange("002415") == "SZ"
    assert _code_to_exchange("300750") == "SZ"


def test_code_to_exchange_bj():
    assert _code_to_exchange("830799") == "BJ"
    assert _code_to_exchange("430047") == "BJ"
```

- [ ] **Step 2: Write router integration test**

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_stocks_endpoint_returns_200():
    resp = client.get("/stocks")
    assert resp.status_code == 200


def test_stocks_filter_by_market():
    resp = client.get("/stocks?market=ZH_A")
    assert resp.status_code == 200


def test_stocks_refresh():
    resp = client.get("/stocks?refresh=true")
    assert resp.status_code == 200


def test_stocks_refresh_with_market():
    resp = client.get("/stocks?market=ZH_A&refresh=true")
    assert resp.status_code == 200
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/test_stock_list.py -v`

- [ ] **Step 4: Commit**

```bash
git add tests/test_stock_list.py
git commit -m "test: add stock list tests"
```

---

### Task 8: Integration smoke test

- [ ] **Step 1: Run all tests**

Run: `pytest -v`
Expected: all tests pass (including existing ones).

- [ ] **Step 2: Start the server and hit the endpoint**

```bash
uvicorn app.main:app &
sleep 2
curl -s http://localhost:8000/stocks | python -m json.tool | head -20
curl -s http://localhost:8000/stocks?market=ZH_A | python -m json.tool | head -20
kill %1
```
