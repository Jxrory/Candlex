# Financial Indicator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `GET /indicator/{symbol}` endpoint caching quarterly financial analysis indicators from East Money.

**Architecture:** New `FinancialIndicatorSource` fetches from akshare; `FinancialIndicatorService` handles DB upsert/query using JSONB storage; route follows existing `/dividend/{symbol}` pattern.

**Tech Stack:** FastAPI, asyncpg, akshare (`stock_financial_analysis_indicator_em`), JSONB (PostgreSQL)

---

### Task 1: DB Schema — Add financial_indicators table

**Files:**
- Modify: `scripts/init_db.sql`

- [ ] **Step 1: Add table DDL to init_db.sql**

Append before the closing of the file:

```sql
CREATE TABLE IF NOT EXISTS financial_indicators (
    symbol       TEXT    NOT NULL,
    report_date  DATE    NOT NULL,
    data         JSONB   NOT NULL,
    source       TEXT    NOT NULL,
    updated_at   TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (symbol, report_date)
);
```

- [ ] **Step 2: Commit**

```bash
git add scripts/init_db.sql
git commit -m "feat: add financial_indicators table"
```

---

### Task 2: Pydantic Schema — FinancialIndicatorRecord

**Files:**
- Modify: `app/schemas.py`

- [ ] **Step 1: Add FinancialIndicatorRecord**

Add after the existing `StockInfoRecord` class:

```python
class FinancialIndicatorRecord(BaseModel):
    symbol: str
    report_date: date
    data: dict
```

- [ ] **Step 2: Commit**

```bash
git add app/schemas.py
git commit -m "feat: add FinancialIndicatorRecord schema"
```

---

### Task 3: Data Source — FinancialIndicatorSource

**Files:**
- Create: `app/sources/financial_indicator.py`

- [ ] **Step 1: Write the source**

```python
import logging

import akshare as ak
import pandas as pd

from app.ak_trace import trace_akshare

logger = logging.getLogger(__name__)


class FinancialIndicatorSource:
    @property
    def name(self) -> str:
        return "financial_indicator_em"

    def _to_raw_code(self, symbol: str) -> str:
        return symbol.split(".")[1]

    @trace_akshare("stock_financial_analysis_indicator_em")
    def _fetch(self, code: str) -> pd.DataFrame:
        return ak.stock_financial_analysis_indicator_em(symbol=code, indicator="单季报")

    async def fetch(self, symbol: str) -> pd.DataFrame:
        code = self._to_raw_code(symbol)
        logger.info("financial indicator source: fetching %s", code)
        df = await self._fetch(code)
        if df.empty:
            logger.warning("financial indicator source: empty result for %s", code)
            return pd.DataFrame()

        rows = []
        report_date_col = None
        for col in df.columns:
            if "report_date" in col.lower() or col in ("REPORT_DATE", "报告期", "截至日期", "截止日期"):
                report_date_col = col
                break

        if report_date_col is None:
            logger.error("financial indicator source: no date column found in %s", list(df.columns))
            return pd.DataFrame()

        for _, row in df.iterrows():
            rd = row[report_date_col]
            if pd.isna(rd):
                continue
            if hasattr(rd, "date"):
                rd = rd.date()

            row_dict = row.drop(report_date_col).dropna().to_dict()
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
        logger.info("financial indicator source: returning %d records for %s", len(result), code)
        return result
```

- [ ] **Step 2: Commit**

```bash
git add app/sources/financial_indicator.py
git commit -m "feat: add FinancialIndicatorSource"
```

---

### Task 4: Service — FinancialIndicatorService

**Files:**
- Create: `app/financial_indicator.py`

- [ ] **Step 1: Write the service**

```python
import json
import logging
from datetime import date

import asyncpg
import pandas as pd

from app.schemas import FinancialIndicatorRecord
from app.sources.financial_indicator import FinancialIndicatorSource

logger = logging.getLogger(__name__)


class FinancialIndicatorService:
    def __init__(self):
        self.source = FinancialIndicatorSource()

    async def get_indicators(
        self,
        pool: asyncpg.Pool,
        symbol: str,
        start: date | None = None,
        end: date | None = None,
    ) -> list[FinancialIndicatorRecord]:
        query = "SELECT symbol, report_date, data FROM financial_indicators WHERE symbol = $1"
        params: list = [symbol]
        if start:
            query += " AND report_date >= $" + str(len(params) + 1)
            params.append(start)
        if end:
            query += " AND report_date <= $" + str(len(params) + 1)
            params.append(end)
        query += " ORDER BY report_date"

        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        return [
            FinancialIndicatorRecord(
                symbol=r["symbol"],
                report_date=r["report_date"],
                data=json.loads(r["data"]) if isinstance(r["data"], str) else dict(r["data"]),
            )
            for r in rows
        ]

    async def sync_symbol(self, pool: asyncpg.Pool, symbol: str) -> int:
        df = await self.source.fetch(symbol)
        if df.empty:
            return 0

        rows: list[tuple] = []
        for _, row in df.iterrows():
            data_json = json.dumps(row["data"], ensure_ascii=False, default=str)
            rows.append((symbol, row["report_date"], data_json, self.source.name))

        async with pool.acquire() as conn:
            await conn.executemany(
                """INSERT INTO financial_indicators (symbol, report_date, data, source)
                   VALUES ($1, $2, $3::jsonb, $4)
                   ON CONFLICT (symbol, report_date) DO UPDATE SET
                       data = EXCLUDED.data,
                       source = EXCLUDED.source,
                       updated_at = NOW()""",
                rows,
            )
        return len(rows)


financial_indicator_service = FinancialIndicatorService()
```

- [ ] **Step 2: Commit**

```bash
git add app/financial_indicator.py
git commit -m "feat: add FinancialIndicatorService"
```

---

### Task 5: Router — GET /indicator/{symbol}

**Files:**
- Modify: `app/router.py`

- [ ] **Step 1: Add import and route**

Add import line after existing `stock_list` import:

```python
from app.financial_indicator import financial_indicator_service
from app.schemas import KlineRecord, DividendRecord, StockInfoRecord, FinancialIndicatorRecord
```

Add route at the end (before EOF):

```python
@router.get("/indicator/{symbol}", response_model=list[FinancialIndicatorRecord])
async def indicator(
    symbol: str = Path(pattern=r"^(SH|SZ|BJ)\.[0-9]{6}$"),
    start: date | None = Query(None),
    end: date | None = Query(None),
    refresh: bool = Query(False),
):
    logger.info("GET /indicator/%s refresh=%s start=%s end=%s", symbol, refresh, start, end)
    pool = await get_pool()
    if refresh:
        count = await financial_indicator_service.sync_symbol(pool, symbol)
        logger.info("GET /indicator/%s sync completed: %d records", symbol, count)
    records = await financial_indicator_service.get_indicators(pool, symbol, start, end)
    logger.info("GET /indicator/%s returned %d records", symbol, len(records))
    return records
```

- [ ] **Step 2: Commit**

```bash
git add app/router.py
git commit -m "feat: add GET /indicator/{symbol} endpoint"
```

---

### Task 6: Tests

**Files:**
- Create: `tests/test_financial_indicator.py`

- [ ] **Step 1: Write tests**

```python
from datetime import date
from fastapi.testclient import TestClient
from app.main import app
from app.schemas import FinancialIndicatorRecord

client = TestClient(app)


def test_indicator_record_defaults():
    """FinancialIndicatorRecord should accept symbol, report_date, data."""
    r = FinancialIndicatorRecord(
        symbol="SH.600519",
        report_date=date(2024, 3, 31),
        data={"basic_eps": 1.5, "roe": 8.5},
    )
    assert r.symbol == "SH.600519"
    assert r.report_date == date(2024, 3, 31)
    assert r.data["basic_eps"] == 1.5
    assert r.data["roe"] == 8.5


def test_indicator_record_empty_data():
    """data field should allow empty dict."""
    r = FinancialIndicatorRecord(
        symbol="SZ.000001",
        report_date=date(2024, 3, 31),
        data={},
    )
    assert r.data == {}


def test_indicator_route_no_refresh():
    """GET /indicator/{symbol} without refresh returns 200."""
    resp = client.get("/indicator/SH.600519")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    if data:
        item = data[0]
        assert "symbol" in item
        assert "report_date" in item
        assert "data" in item
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `pytest tests/test_financial_indicator.py -v`
Expected: all 3 tests PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_financial_indicator.py
git commit -m "test: add financial indicator tests"
```
