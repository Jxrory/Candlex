# mootdx Source Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add mootdx as a K-line data source in the multi-source failover chain.

**Architecture:** New `MootdxSource` implementing `BaseSource`, wrapping synchronous mootdx calls with `run_in_executor`. Registered in `SOURCES` dict in `service.py`.

**Tech Stack:** Python 3.11+, pandas, mootdx 0.11.7

---

### Task 1: Create `app/sources/mootdx.py`

**Files:**
- Create: `app/sources/mootdx.py`
- Test: `tests/test_service.py` (add test to existing file)

- [ ] **Step 1: Add mootdx source format test to `tests/test_service.py`**

Insert after `test_eastmoney_source_format` (line 60):

```python
@pytest.mark.asyncio
async def test_mootdx_source_format():
    from app.sources.mootdx import MootdxSource
    try:
        df = await MootdxSource().fetch("SH.600300", _default_start(), _default_end())
    except Exception as e:
        pytest.skip(f"mootdx source unavailable: {e}")

    assert not df.empty
    assert list(df.columns) == ["date", "open", "high", "low", "close", "volume", "amount"]
    assert df["date"].dtype.kind in ("M", "O")
    for col in ("open", "high", "low", "close", "amount"):
        assert df[col].dtype.kind == "f", f"{col} dtype={df[col].dtype}"
    assert df["volume"].dtype.kind in ("i", "u", "f")
    assert (df["high"] >= df["low"]).all()
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
source .venv/bin/activate && pytest tests/test_service.py::test_mootdx_source_format -v
```

Expected: `FAIL` with `ModuleNotFoundError: No module named 'app.sources.mootdx'` (or similar import error).

- [ ] **Step 3: Write minimal implementation**

Create `app/sources/mootdx.py`:

```python
import asyncio
import logging
from datetime import date
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

from app.sources.base import BaseSource

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=2)


class MootdxSource(BaseSource):
    @property
    def name(self) -> str:
        return "mootdx"

    async def fetch(
        self, symbol: str, start_date: date, end_date: date
    ) -> pd.DataFrame:
        code = symbol.split(".")[1]
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")

        logger.info("mootdx fetch raw %s [%s, %s]", code, start_str, end_str)

        def _fetch() -> pd.DataFrame:
            from mootdx.quotes import Quotes
            client = Quotes.factory(market="std")
            return client.k(symbol=code, begin=start_str, end=end_str)

        loop = asyncio.get_running_loop()
        raw = await loop.run_in_executor(_executor, _fetch)

        if raw is None or (isinstance(raw, pd.DataFrame) and raw.empty):
            logger.warning("mootdx raw data empty for %s", code)
            return pd.DataFrame()

        result = raw[["date", "open", "high", "low", "close", "vol", "amount"]].copy()
        result["volume"] = result["vol"] * 100
        result.drop(columns=["vol"], inplace=True)
        result["date"] = pd.to_datetime(result["date"])

        logger.info("mootdx returning %d rows", len(result))
        return result[["date", "open", "high", "low", "close", "volume", "amount"]]
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
source .venv/bin/activate && pytest tests/test_service.py::test_mootdx_source_format -v
```

Expected: `PASS` (or `SKIP` if TDX servers are unreachable).

- [ ] **Step 5: Commit**

```bash
git add app/sources/mootdx.py tests/test_service.py
git commit -m "feat: add mootdx K-line source"
```

---

### Task 2: Register MootdxSource in service.py

**Files:**
- Modify: `app/service.py`

- [ ] **Step 1: Add import and register in SOURCES**

In `app/service.py`, add after line 13 (`from app.sources.sina import SinaSource`):

```python
from app.sources.mootdx import MootdxSource
```

Add to the `SOURCES` dict (after line 23):

```python
SOURCES: dict[str, BaseSource] = {
    "sina": SinaSource(),
    "tencent": TencentSource(),
    "eastmoney": EastMoneySource(),
    "mootdx": MootdxSource(),
}
```

- [ ] **Step 2: Verify the import works**

```bash
source .venv/bin/activate && python3 -c "from app.service import SOURCES; print(list(SOURCES.keys()))"
```

Expected: `['sina', 'tencent', 'eastmoney', 'mootdx']` (no import errors).

- [ ] **Step 3: Run existing tests to ensure no regressions**

```bash
source .venv/bin/activate && pytest tests/ -v
```

Expected: All previously passing tests still pass (mootdx test may skip if servers unreachable).

- [ ] **Step 4: Commit**

```bash
git add app/service.py
git commit -m "feat: register mootdx in source failover chain"
```
