# Indicators API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `GET /indicators/{symbol}` route that returns K-line data plus computed technical indicators.

**Architecture:** New `app/indicators_service.py` handles spec parsing and indicator computation. Route handler in `app/router.py` calls `get_kline()` from existing service for data, then `compute_many()` from `tools/indicators.py` for indicators. Pure on-demand compute — no indicator caching.

**Tech Stack:** FastAPI, pandas, numpy (via existing `app/tools/indicators.py`)

---

### Task 1: parse_specs — unit tests + implementation

**Files:**
- Create: `tests/test_indicators.py`
- Create: `app/indicators_service.py`

**Step 1: Write the failing tests**

`tests/test_indicators.py`:
```python
from datetime import date
import pytest
from app.tools.indicators import IndicatorSpec


def test_parse_shorthand_no_params():
    from app.indicators_service import parse_specs
    result = parse_specs(["macd"])
    assert result == [IndicatorSpec("macd")]


def test_parse_shorthand_with_params():
    from app.indicators_service import parse_specs
    result = parse_specs(["ma:5"])
    assert result == [IndicatorSpec("ma", {"n": 5})]


def test_parse_shorthand_multi_params():
    from app.indicators_service import parse_specs
    result = parse_specs(["boll:20,2.0"])
    assert result == [IndicatorSpec("boll", {"n": 20, "k": 2.0})]


def test_parse_json_format():
    from app.indicators_service import parse_specs
    result = parse_specs(['[{"name":"ma","params":{"n":5}}]'])
    assert result == [IndicatorSpec("ma", {"n": 5})]


def test_parse_mixed():
    from app.indicators_service import parse_specs
    result = parse_specs(["ma:5", '[{"name":"macd","params":{"fast":12,"slow":26,"signal":9}}]'])
    assert result == [
        IndicatorSpec("ma", {"n": 5}),
        IndicatorSpec("macd", {"fast": 12, "slow": 26, "signal": 9}),
    ]


def test_parse_empty():
    from app.indicators_service import parse_specs
    result = parse_specs([])
    assert result == []


def test_parse_unknown_indicator():
    from app.indicators_service import parse_specs
    with pytest.raises(ValueError, match="unsupported indicator"):
        parse_specs(["unknown:5"])


def test_parse_unknown_indicator_json():
    from app.indicators_service import parse_specs
    with pytest.raises(ValueError, match="unsupported indicator"):
        parse_specs(['[{"name":"INVALID","params":{}}]'])
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_indicators.py -v`
Expected: 8 FAILED (ImportError / function not defined)

**Step 3: Implement parse_specs**

`app/indicators_service.py`:
```python
import json
import logging
from typing import Any

import numpy as np
import pandas as pd

from app.service import get_kline
from app.tools.indicators import IndicatorSpec, SUPPORTED, compute_many

logger = logging.getLogger(__name__)

INDICATOR_PARAMS: dict[str, list[str]] = {
    "ma": ["n"],
    "ema": ["n"],
    "macd": ["fast", "slow", "signal"],
    "rsi": ["n"],
    "boll": ["n", "k"],
    "atr": ["n"],
    "kdj": ["n", "m1", "m2"],
}


def parse_specs(raw: list[str]) -> list[IndicatorSpec]:
    specs: list[IndicatorSpec] = []
    for val in raw:
        val = val.strip()
        if not val:
            continue
        if val.startswith("["):
            parsed = json.loads(val)
            for item in parsed:
                name = item["name"].lower()
                if name not in SUPPORTED:
                    raise ValueError(f"unsupported indicator: {name}")
                specs.append(IndicatorSpec(name, item.get("params")))
        else:
            parts = val.split(":")
            name = parts[0].lower()
            if name not in SUPPORTED:
                raise ValueError(f"unsupported indicator: {name}")
            params = None
            if len(parts) > 1 and parts[1]:
                raw_params = parts[1].split(",")
                param_names = INDICATOR_PARAMS.get(name, [])
                params = {}
                for i, p in enumerate(raw_params):
                    p = p.strip()
                    if i < len(param_names):
                        key = param_names[i]
                        try:
                            params[key] = int(p) if "." not in p else float(p)
                        except ValueError:
                            params[key] = p
            specs.append(IndicatorSpec(name, params if params else None))

    seen: set[tuple] = set()
    deduped: list[IndicatorSpec] = []
    for s in specs:
        items = tuple(sorted((s.params or {}).items()))
        key = (s.name, items)
        if key not in seen:
            seen.add(key)
            deduped.append(s)
    return deduped
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_indicators.py -v`
Expected: 8 PASSED

**Step 5: Commit**

```bash
git add tests/test_indicators.py app/indicators_service.py
git commit -m "feat: add parse_specs for indicator spec parsing"
```

---

### Task 2: get_indicators implementation

**Files:**
- Modify: `app/indicators_service.py` (add get_indicators + helpers)

**Step 1: Add get_indicators function**

Append to `app/indicators_service.py`:
```python
async def get_indicators(
    symbol: str,
    start: date,
    end: date,
    adjust: str | None = None,
    specs: list[IndicatorSpec] | None = None,
) -> list[dict[str, Any]]:
    records = await get_kline(symbol, start, end, adjust)
    if not records:
        return []
    df = pd.DataFrame([r.model_dump() for r in records])
    if specs:
        df = compute_many(df, specs)
    df = df.replace({np.nan: None})
    return df.to_dict(orient="records")
```

Add the missing import at top of file:
```python
from datetime import date
```

**Step 2: Verify it imports cleanly**

Run: `python -c "from app.indicators_service import get_indicators; print('OK')"`
Expected: OK

**Step 3: Commit**

```bash
git add app/indicators_service.py
git commit -m "feat: add get_indicators compute function"
```

---

### Task 3: Add route to router.py

**Files:**
- Modify: `app/router.py`

**Step 1: Write the route**

Add to `app/router.py`, after the existing `/kline` route:

```python
@router.get("/indicators/{symbol}")
async def indicators(
    symbol: str = Path(pattern=r"^(SH|SZ|BJ)\.[0-9]{6}$"),
    start: date | None = Query(None),
    end: date | None = Query(None),
    adjust: str | None = Query(None, pattern="^(qfq|hfq)$"),
    i: list[str] = Query(default_factory=list),
):
    today = date.today()
    if end is None:
        end = today
    if start is None:
        start = today - timedelta(days=365)

    logger.info("GET /indicators/%s start=%s end=%s adjust=%s i=%s", symbol, start, end, adjust, i)
    from app.indicators_service import get_indicators, parse_specs
    specs = parse_specs(i)
    result = await get_indicators(symbol, start, end, adjust, specs)
    logger.info("GET /indicators/%s returned %d records", symbol, len(result))
    return result
```

**Step 2: Import datetime.date and timedelta (already at top of router.py)**

Check that `from datetime import date, timedelta` is already imported (line 2 of router.py — it is).

**Step 3: Verify route registers**

Run: `python -c "from app.main import app; routes = [r.path for r in app.routes]; assert '/indicators/{symbol}' in routes; print('OK')"`
Expected: OK

**Step 4: Commit**

```bash
git add app/router.py
git commit -m "feat: add GET /indicators/{symbol} route"
```

---

### Task 4: Integration tests

**Files:**
- Modify: `tests/test_router.py`

**Step 1: Add integration tests**

Append to `tests/test_router.py`:

```python
def test_indicators_basic():
    resp = client.get("/indicators/SH.600519?start=2024-01-01&end=2024-01-10&i=ma:5")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    if data:
        record = data[0]
        assert "date" in record
        assert "close" in record
        assert "ma5" in record


def test_indicators_multiple():
    resp = client.get("/indicators/SH.600519?start=2024-01-01&end=2024-01-10&i=ma:5&i=ma:10&i=macd")
    assert resp.status_code == 200
    data = resp.json()
    if data:
        record = data[0]
        assert "ma5" in record
        assert "ma10" in record
        assert "macd_dif" in record


def test_indicators_no_i_returns_raw_kline():
    resp = client.get("/indicators/SH.600519?start=2024-01-01&end=2024-01-10")
    assert resp.status_code == 200
    data = resp.json()
    if data:
        record = data[0]
        assert "date" in record
        assert "close" in record
        assert "ma5" not in record


def test_indicators_bad_symbol():
    resp = client.get("/indicators/INVALID?i=ma:5")
    assert resp.status_code == 422


def test_indicators_unknown_indicator():
    resp = client.get("/indicators/SH.600519?i=unknown:5")
    assert resp.status_code == 422


def test_indicators_invalid_adjust():
    resp = client.get("/indicators/SH.600519?adjust=bad&i=ma:5")
    assert resp.status_code == 422


def test_indicators_with_adjust():
    resp = client.get("/indicators/SH.600519?start=2024-01-01&end=2024-01-10&adjust=qfq&i=ma:5")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
```

**Step 2: Run integration tests**

Run: `pytest tests/test_router.py::test_indicators_basic tests/test_router.py::test_indicators_multiple tests/test_router.py::test_indicators_no_i_returns_raw_kline tests/test_router.py::test_indicators_bad_symbol tests/test_router.py::test_indicators_unknown_indicator tests/test_router.py::test_indicators_invalid_adjust tests/test_router.py::test_indicators_with_adjust -v`
Expected: 7 PASSED (may skip if DB unavailable for the first three)

**Step 3: Run full test suite**

Run: `pytest -v`
Expected: All existing tests + new tests passing

**Step 4: Commit**

```bash
git add tests/test_router.py
git commit -m "test: add integration tests for /indicators endpoint"
```
