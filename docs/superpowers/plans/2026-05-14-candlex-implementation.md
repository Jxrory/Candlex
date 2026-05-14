# CandleX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a daily K-line caching service with FastAPI + TimescaleDB + multi-source akshare failover

**Architecture:** REST API using asyncpg for async PostgreSQL, with a service layer that checks cache first, then falls back to akshare data sources (sina → tencent → eastmoney) for missing/expired data

**Tech Stack:** Python 3.11+, FastAPI, asyncpg, akshare, pydantic-settings, TimescaleDB 2.27

---

### Task 1: Project Scaffolding & Configuration

**Files:**
- Create: `app/__init__.py`
- Create: `app/config.py`
- Create: `pyproject.toml`

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p app models sources scripts
touch app/__init__.py
```

- [ ] **Step 2: Create pyproject.toml**

```toml
[project]
name = "candlex"
version = "0.1.0"
description = "Daily K-line caching service with akshare multi-source failover"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.34",
    "asyncpg>=0.30",
    "pandas>=2.0",
    "akshare>=1.18",
    "pydantic-settings>=2.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.25",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 3: Create config.py**

```python
from pydantic_settings import BaseSettings
from typing import ClassVar


class Settings(BaseSettings):
    db_dsn: str = "postgresql://candlex:candlex@localhost:5432/candlex"
    db_min_connections: int = 2
    db_max_connections: int = 10

    cache_ttl_today_seconds: int = 60
    cache_ttl_recent_days: int = 5
    cache_ttl_recent_seconds: int = 300
    source_priority: list[str] = ["sina", "tencent", "eastmoney"]

    model_config: ClassVar[dict] = {"env_prefix": "CANDLEX_", "env_file": ".env"}


settings = Settings()
```

- [ ] **Step 4: Commit**

```bash
git add -A && git commit -m "chore: scaffold project and configuration"
```

---

### Task 2: Database Schema & Connection

**Files:**
- Create: `scripts/init_db.sql`
- Create: `app/database.py`

- [ ] **Step 1: Create init_db.sql**

```sql
CREATE TABLE IF NOT EXISTS kline_data (
    symbol        TEXT    NOT NULL,
    date          DATE    NOT NULL,
    open          NUMERIC(10,3),
    high          NUMERIC(10,3),
    low           NUMERIC(10,3),
    close         NUMERIC(10,3),
    volume        BIGINT,
    amount        NUMERIC(15,2),
    factor_qfq    NUMERIC(10,6),
    factor_hfq    NUMERIC(10,6),
    source        TEXT    NOT NULL,
    updated_at    TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (symbol, date)
);

SELECT create_hypertable('kline_data', 'date', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_kline_symbol_date ON kline_data (symbol, date DESC);
```

- [ ] **Step 2: Create database.py**

```python
import asyncpg
from app.config import settings


pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global pool
    if pool is None:
        pool = await asyncpg.create_pool(
            dsn=settings.db_dsn,
            min_size=settings.db_min_connections,
            max_size=settings.db_max_connections,
        )
    return pool


async def close_pool() -> None:
    global pool
    if pool:
        await pool.close()
        pool = None
```

- [ ] **Step 3: Commit**

```bash
git add -A && git commit -m "feat: add database schema and connection pool"
```

---

### Task 3: Pydantic Schemas

**Files:**
- Create: `app/schemas.py`

- [ ] **Step 1: Create schemas.py**

```python
from datetime import date
from pydantic import BaseModel


class KlineRecord(BaseModel):
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int | None = None
    amount: float | None = None
    factor_qfq: float | None = None
    factor_hfq: float | None = None
```

- [ ] **Step 2: Commit**

```bash
git add -A && git commit -m "feat: add pydantic schemas"
```

---

### Task 4: Data Source Abstraction

**Files:**
- Create: `app/sources/__init__.py`
- Create: `app/sources/base.py`

- [ ] **Step 1: Create sources/__init__.py** (empty)

- [ ] **Step 2: Create sources/base.py**

```python
from abc import ABC, abstractmethod
from datetime import date
import pandas as pd


class BaseSource(ABC):
    @abstractmethod
    async def fetch(
        self, symbol: str, start_date: date, end_date: date
    ) -> pd.DataFrame:
        """Returns DataFrame with columns: date, open, high, low, close, volume, amount, factor_qfq, factor_hfq"""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        ...
```

- [ ] **Step 3: Commit**

```bash
git add -A && git commit -m "feat: add data source abstraction"
```

---

### Task 5: Sina Source Implementation

**Files:**
- Create: `app/sources/sina.py`

- [ ] **Step 1: Create sina.py**

```python
from datetime import date
import akshare as ak
import pandas as pd

from app.sources.base import BaseSource


class SinaSource(BaseSource):
    @property
    def name(self) -> str:
        return "sina"

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

        factor_qfq = ak.stock_zh_a_daily(
            symbol=sina_symbol, start_date=start_str, end_date=end_str, adjust="qfq-factor"
        )
        factor_hfq = ak.stock_zh_a_daily(
            symbol=sina_symbol, start_date=start_str, end_date=end_str, adjust="hfq-factor"
        )

        result = raw[["open", "high", "low", "close", "volume", "amount"]].copy()
        result["date"] = raw.index
        result.reset_index(drop=True, inplace=True)

        factor_qfq["date"] = pd.to_datetime(factor_qfq["date"]).dt.date
        factor_hfq["date"] = pd.to_datetime(factor_hfq["date"]).dt.date

        result = result.merge(
            factor_qfq[["date", "qfq_factor"]], on="date", how="left"
        )
        result = result.merge(
            factor_hfq[["date", "hfq_factor"]], on="date", how="left"
        )
        result.rename(
            columns={"qfq_factor": "factor_qfq", "hfq_factor": "factor_hfq"},
            inplace=True,
        )
        result[["factor_qfq", "factor_hfq"]] = result[
            ["factor_qfq", "factor_hfq"]
        ].ffill()

        return result
```

- [ ] **Step 2: Commit**

```bash
git add -A && git commit -m "feat: add sina data source"
```

---

### Task 6: Tencent Source Implementation

**Files:**
- Create: `app/sources/tencent.py`

- [ ] **Step 1: Create tencent.py**

```python
from datetime import date
import akshare as ak
import pandas as pd

from app.sources.base import BaseSource


class TencentSource(BaseSource):
    @property
    def name(self) -> str:
        return "tencent"

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

        raw_qfq = ak.stock_zh_a_hist_tx(
            symbol=tx_symbol, start_date=start_str, end_date=end_str, adjust="qfq"
        )
        raw_hfq = ak.stock_zh_a_hist_tx(
            symbol=tx_symbol, start_date=start_str, end_date=end_str, adjust="hfq"
        )

        result = raw[["date", "open", "close", "high", "low", "amount"]].copy()
        result["volume"] = None

        raw_qfq = raw_qfq[["date", "close"]].rename(columns={"close": "close_qfq"})
        raw_hfq = raw_hfq[["date", "close"]].rename(columns={"close": "close_hfq"})

        result = result.merge(raw_qfq, on="date", how="left")
        result = result.merge(raw_hfq, on="date", how="left")
        result["factor_qfq"] = (result["close_qfq"] / result["close"]).round(6)
        result["factor_hfq"] = (result["close_hfq"] / result["close"]).round(6)
        result.drop(columns=["close_qfq", "close_hfq"], inplace=True)

        return result
```

- [ ] **Step 2: Commit**

```bash
git add -A && git commit -m "feat: add tencent data source"
```

---

### Task 7: EastMoney Source Implementation

**Files:**
- Create: `app/sources/eastmoney.py`

- [ ] **Step 1: Create eastmoney.py**

```python
from datetime import date
import akshare as ak
import pandas as pd

from app.sources.base import BaseSource

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

        raw_qfq = ak.stock_zh_a_hist(
            symbol=code, period="daily",
            start_date=start_str, end_date=end_str, adjust="qfq",
        )
        raw_hfq = ak.stock_zh_a_hist(
            symbol=code, period="daily",
            start_date=start_str, end_date=end_str, adjust="hfq",
        )

        result = raw.rename(columns=COLUMN_MAP)
        result["date"] = pd.to_datetime(result["date"]).dt.date

        raw_qfq = raw_qfq.rename(columns=COLUMN_MAP)[["date", "close"]].rename(
            columns={"close": "close_qfq"}
        )
        raw_hfq = raw_hfq.rename(columns=COLUMN_MAP)[["date", "close"]].rename(
            columns={"close": "close_hfq"}
        )

        result = result.merge(raw_qfq, on="date", how="left")
        result = result.merge(raw_hfq, on="date", how="left")
        result["factor_qfq"] = (result["close_qfq"] / result["close"]).round(6)
        result["factor_hfq"] = (result["close_hfq"] / result["close"]).round(6)
        result.drop(columns=["close_qfq", "close_hfq"], inplace=True)

        return result[["date", "open", "high", "low", "close", "volume", "amount", "factor_qfq", "factor_hfq"]]
```

- [ ] **Step 2: Commit**

```bash
git add -A && git commit -m "feat: add eastmoney data source"
```

---

### Task 8: Service Layer — Cache Orchestration & Price Adjustment

**Files:**
- Create: `app/service.py`

**Logic overview:**

1. Query DB for cached records in [start, end]
2. Find missing date ranges and expired recent data
3. For each missing range, try sources in priority order
4. Upsert new data into DB
5. Merge cached + new → apply adjust if needed → return

- [ ] **Step 1: Create service.py**

```python
from datetime import date, datetime, timedelta

import asyncpg
import pandas as pd

from app.config import settings
from app.database import get_pool
from app.schemas import KlineRecord
from app.sources.base import BaseSource
from app.sources.sina import SinaSource
from app.sources.tencent import TencentSource
from app.sources.eastmoney import EastMoneySource

SOURCES: dict[str, BaseSource] = {
    "sina": SinaSource(),
    "tencent": TencentSource(),
    "eastmoney": EastMoneySource(),
}


def _needs_refresh(updated_at: datetime | None, target_date: date, today: date) -> bool:
    if updated_at is None:
        return True
    days_ago = (today - target_date).days
    if days_ago == 0:
        ttl = settings.cache_ttl_today_seconds
    elif days_ago <= settings.cache_ttl_recent_days:
        ttl = settings.cache_ttl_recent_seconds
    else:
        return False
    age = (datetime.now() - updated_at).total_seconds()
    return age > ttl


async def query_cached(
    pool: asyncpg.Pool, symbol: str, start: date, end: date
) -> list[asyncpg.Record]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT date, open, high, low, close, volume, amount,
                      factor_qfq, factor_hfq, updated_at
               FROM kline_data
               WHERE symbol = $1 AND date BETWEEN $2 AND $3
               ORDER BY date""",
            symbol, start, end,
        )
    return rows


def _df_to_rows(df: pd.DataFrame, symbol: str, source: str) -> list[tuple]:
    rows: list[tuple] = []
    for _, row in df.iterrows():
        rows.append((
            symbol,
            row["date"],
            float(row["open"]) if pd.notna(row.get("open")) else None,
            float(row["high"]) if pd.notna(row.get("high")) else None,
            float(row["low"]) if pd.notna(row.get("low")) else None,
            float(row["close"]) if pd.notna(row.get("close")) else None,
            int(row["volume"]) if pd.notna(row.get("volume")) else None,
            float(row["amount"]) if pd.notna(row.get("amount")) else None,
            float(row["factor_qfq"]) if pd.notna(row.get("factor_qfq")) else None,
            float(row["factor_hfq"]) if pd.notna(row.get("factor_hfq")) else None,
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
               (symbol, date, open, high, low, close, volume, amount,
                factor_qfq, factor_hfq, source, updated_at)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,NOW())
               ON CONFLICT (symbol, date)
               DO UPDATE SET
                   open=EXCLUDED.open, high=EXCLUDED.high,
                   low=EXCLUDED.low, close=EXCLUDED.close,
                   volume=EXCLUDED.volume, amount=EXCLUDED.amount,
                   factor_qfq=EXCLUDED.factor_qfq,
                   factor_hfq=EXCLUDED.factor_hfq,
                   source=EXCLUDED.source,
                   updated_at=NOW()""",
            rows,
        )


def _apply_adjust(
    records: list[KlineRecord], adjust: str | None
) -> list[KlineRecord]:
    if adjust not in ("qfq", "hfq"):
        return records
    factor_key = f"factor_{adjust}"
    adjusted: list[KlineRecord] = []
    for r in records:
        factor = getattr(r, factor_key, None)
        if factor and factor != 0:
            r.open = round(r.open * factor, 3)
            r.high = round(r.high * factor, 3)
            r.low = round(r.low * factor, 3)
            r.close = round(r.close * factor, 3)
        adjusted.append(r)
    return adjusted


def _rows_to_records(rows: list[asyncpg.Record]) -> list[KlineRecord]:
    return [
        KlineRecord(
            date=r["date"],
            open=float(r["open"]) if r["open"] else 0.0,
            high=float(r["high"]) if r["high"] else 0.0,
            low=float(r["low"]) if r["low"] else 0.0,
            close=float(r["close"]) if r["close"] else 0.0,
            volume=int(r["volume"]) if r["volume"] else None,
            amount=float(r["amount"]) if r["amount"] else None,
            factor_qfq=float(r["factor_qfq"]) if r["factor_qfq"] else None,
            factor_hfq=float(r["factor_hfq"]) if r["factor_hfq"] else None,
        )
        for r in rows
    ]


async def get_kline(
    symbol: str,
    start: date,
    end: date,
    adjust: str | None = None,
) -> list[KlineRecord]:
    pool = await get_pool()
    today = date.today()

    cached = await query_cached(pool, symbol, start, end)

    if cached:
        cached_dates = {r["date"] for r in cached}
        all_dates = {
            start + timedelta(days=i) for i in range((end - start).days + 1)
        }
        missing_dates = sorted(all_dates - cached_dates)

        refresh_needed = [
            r["date"] for r in cached
            if _needs_refresh(r["updated_at"], r["date"], today)
        ]

        if missing_dates or refresh_needed:
            fetch_start = min(
                (missing_dates + refresh_needed + [start])
            )
            fetch_end = end

            for source_name in settings.source_priority:
                source = SOURCES.get(source_name)
                if not source:
                    continue
                try:
                    df = await source.fetch(symbol, fetch_start, fetch_end)
                    if not df.empty:
                        await upsert_kline(pool, symbol, df, source_name)
                        break
                except Exception:
                    continue

            cached = await query_cached(pool, symbol, start, end)
    else:
        for source_name in settings.source_priority:
            source = SOURCES.get(source_name)
            if not source:
                continue
            try:
                df = await source.fetch(symbol, start, end)
                if not df.empty:
                    await upsert_kline(pool, symbol, df, source_name)
                    break
            except Exception:
                continue

        cached = await query_cached(pool, symbol, start, end)

    records = _rows_to_records(cached)
    return _apply_adjust(records, adjust)
```

- [ ] **Step 2: Commit**

```bash
git add -A && git commit -m "feat: add service layer with caching and multi-source failover"
```

---

### Task 9: Router

**Files:**
- Create: `app/router.py`

- [ ] **Step 1: Create router.py**

```python
```python
from datetime import date, timedelta
from fastapi import APIRouter, Query

from app.schemas import KlineRecord
from app.service import get_kline

router = APIRouter()


@router.get("/kline/{symbol}", response_model=list[KlineRecord])
async def kline(
    symbol: str,
    start: date | None = Query(None),
    end: date | None = Query(None),
    adjust: str | None = Query(None, pattern="^(qfq|hfq)$"),
):
    today = date.today()
    if end is None:
        end = today
    if start is None:
        start = today - timedelta(days=365)

    return await get_kline(symbol, start, end, adjust)
```

- [ ] **Step 2: Commit**

```bash
git add -A && git commit -m "feat: add kline API router"
```

---

### Task 10: Main Entry Point

**Files:**
- Create: `app/main.py`

- [ ] **Step 1: Create main.py**

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import get_pool, close_pool
from app.router import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_pool()
    yield
    await close_pool()


app = FastAPI(title="CandleX", lifespan=lifespan)
app.include_router(router)
```

- [ ] **Step 2: Commit**

```bash
git add -A && git commit -m "feat: add FastAPI application entry"
```

---

### Task 11: Dockerfile

**Files:**
- Create: `Dockerfile`

- [ ] **Step 1: Create Dockerfile**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Commit**

```bash
git add -A && git commit -m "chore: add Dockerfile"
```

---

### Task 12: Integration Tests

**Files:**
- Create: `tests/conftest.py`
- Create: `tests/test_service.py`
- Create: `tests/test_router.py`

- [ ] **Step 1: Create conftest.py**

```python
import pytest
from datetime import date


@pytest.fixture
def sample_kline_records():
    return [
        {"date": date(2024, 1, 2), "open": 10.0, "high": 11.0, "low": 9.5,
         "close": 10.5, "volume": 1000000, "amount": 1.05e7,
         "factor_qfq": 1.0, "factor_hfq": 1.5, "updated_at": None},
        {"date": date(2024, 1, 3), "open": 10.5, "high": 11.2, "low": 10.2,
         "close": 11.0, "volume": 1200000, "amount": 1.3e7,
         "factor_qfq": 1.0, "factor_hfq": 1.5, "updated_at": None},
    ]


@pytest.fixture
def sample_records(sample_kline_records):
    from app.service import _rows_to_records
    return _rows_to_records(sample_kline_records)
```

- [ ] **Step 2: Create test_service.py**

```python
import pytest
from app.service import _apply_adjust


def test_no_adjust_returns_raw(sample_records):
    result = _apply_adjust(sample_records, None)
    assert result[0].close == 10.5


def test_qfq_adjust_applies_factor(sample_records):
    result = _apply_adjust(sample_records, "qfq")
    assert result[0].close == 10.5  # factor_qfq=1.0


def test_hfq_adjust_applies_factor(sample_records):
    result = _apply_adjust(sample_records, "hfq")
    assert result[0].close == pytest.approx(15.75)  # 10.5 * 1.5
```

- [ ] **Step 3: Create test_router.py**

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_route_returns_200():
    resp = client.get("/kline/SH.600519?start=2024-01-01&end=2024-01-03")
    assert resp.status_code == 200


def test_bad_symbol_format():
    resp = client.get("/kline/INVALID?start=2024-01-01&end=2024-01-03")
    assert resp.status_code == 200  # graceful degradation


def test_invalid_adjust():
    resp = client.get("/kline/SH.600519?adjust=invalid")
    assert resp.status_code == 422
```

- [ ] **Step 4: Run tests**

```bash
pip install -e ".[dev]" && pytest -v
```

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "test: add unit and integration tests"
```
