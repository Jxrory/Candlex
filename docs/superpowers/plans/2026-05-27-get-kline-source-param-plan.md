# get_kline 可选数据源参数 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `get_kline` 支持可选 `source` 参数，路由和 kline_sync 透传，并添加各数据源格式验证测试。

**Architecture:** 在 `get_kline` 内将指定 source 插入 priority 列表头部（优先尝试，失败回退）。各调用方透传参数，不改现有行为。

**Tech Stack:** FastAPI, asyncpg, pytest, pandas, unittest.mock

---

### Task 1: `get_kline` 新增 source 参数 + effective_priority 逻辑

**Files:**
- Modify: `app/service.py:122-191`

- [ ] **Step 1: 修改 `get_kline` 签名，添加 source 参数**

`app/service.py` 第 122 行，签名改为：
```python
async def get_kline(
    symbol: str,
    start: date,
    end: date,
    adjust: str | None = None,
    source: str | None = None,
) -> list[KlineRecord]:
```

- [ ] **Step 2: 在 `get_kline` 中添加 effective_priority 逻辑**

在第 131 行（`await calendar_service.ensure_fresh()` 之后），插入：
```python
    effective_priority = list(settings.source_priority)
    if source:
        if source in effective_priority:
            effective_priority.remove(source)
        effective_priority.insert(0, source)
```

然后将两处数据获取循环（约 153 行和 168 行）中的 `settings.source_priority` 替换为 `effective_priority`。

- [ ] **Step 3: 运行现有测试，确保未破坏现有功能**

Run: `pytest tests/test_service.py -v`
Expected: 全部 PASS

- [ ] **Step 4: Commit**

```bash
git add app/service.py
git commit -m "feat: get_kline supports optional source param"
```

---

### Task 2: Router 新增 source query param

**Files:**
- Modify: `app/router.py:41-57`

- [ ] **Step 1: 给 `/kline/{symbol}` 路由添加 source 参数**

`app/router.py:42-47`，在 `adjust` 参数后添加：
```python
    source: str | None = Query(None),
```

第 55 行传参：
```python
    records = await get_kline(symbol, start, end, adjust, source=source)
```

- [ ] **Step 2: Commit**

```bash
git add app/router.py
git commit -m "feat: /kline/{symbol} supports ?source= query param"
```

---

### Task 3: KlineSyncService 新增 source 参数

**Files:**
- Modify: `app/kline_sync.py:15-40`

- [ ] **Step 1: 修改 `sync_one` 签名**

```python
    async def sync_one(self, pool: asyncpg.Pool, source: str | None = None) -> int:
```

第 30 行传参：
```python
            records = await get_kline(symbol, Y2000, yesterday, source=source)
```

- [ ] **Step 2: Commit**

```bash
git add app/kline_sync.py
git commit -m "feat: KlineSyncService.sync_one accepts source param"
```

---

### Task 4: 数据源格式验证测试（test_service.py）

**Files:**
- Modify: `tests/test_service.py`
- Test: `tests/test_service.py`

- [ ] **Step 1: 添加 SinaSource 格式验证测试**

```python
from datetime import date
from unittest.mock import patch, MagicMock, AsyncMock
import pandas as pd
import pytest


def test_sina_source_format():
    mock_raw = pd.DataFrame({
        "date": pd.to_datetime(["2024-01-02", "2024-01-03"]),
        "open": [10.0, 10.5],
        "high": [11.0, 11.2],
        "low": [9.5, 10.2],
        "close": [10.5, 11.0],
        "volume": [1000000, 1200000],
        "amount": [1.05e7, 1.3e7],
    })
    with patch("app.sources.sina.ak.stock_zh_a_daily", return_value=mock_raw):
        from app.sources.sina import SinaSource
        df = SinaSource().fetch("sh600519", date(2024,1,1), date(2024,1,31))

    assert list(df.columns) == ["date", "open", "high", "low", "close", "volume", "amount"]
    assert df["date"].dtype.kind in ("M", "O")  # datetime or object
    for col in ("open", "high", "low", "close", "amount"):
        assert df[col].dtype.kind == "f"
    assert df["volume"].dtype.kind in ("i", "u", "f")
    assert (df["high"] >= df["open"]).all()
    assert (df["high"] >= df["close"]).all()
    assert (df["high"] >= df["low"]).all()
```

- [ ] **Step 2: 运行验证失败**

Run: `pytest tests/test_service.py::test_sina_source_format -v`
Expected: PASS

- [ ] **Step 3: 添加 TencentSource 格式验证测试**

```python
def test_tencent_source_format():
    mock_raw = pd.DataFrame({
        "date": pd.to_datetime(["2024-01-02", "2024-01-03"]),
        "open": [10.0, 10.5],
        "close": [10.5, 11.0],
        "high": [11.0, 11.2],
        "low": [9.5, 10.2],
        "amount": [1.05e7, 1.3e7],
    })
    with patch("app.sources.tencent.ak.stock_zh_a_hist_tx", return_value=mock_raw):
        from app.sources.tencent import TencentSource
        df = TencentSource().fetch("SH600519", date(2024,1,1), date(2024,1,31))

    assert list(df.columns) == ["date", "open", "close", "high", "low", "amount"]
    assert df["volume"].isna().all()
    for col in ("open", "close", "high", "low", "amount"):
        assert df[col].dtype.kind == "f"
    assert (df["high"] >= df["open"]).all()
    assert (df["high"] >= df["close"]).all()
    assert (df["high"] >= df["low"]).all()
```

- [ ] **Step 4: 运行验证通过**

Run: `pytest tests/test_service.py::test_tencent_source_format -v`
Expected: PASS

- [ ] **Step 5: 添加 EastMoneySource 格式验证测试**

```python
def test_eastmoney_source_format():
    mock_raw = pd.DataFrame({
        "日期": pd.to_datetime(["2024-01-02", "2024-01-03"]),
        "开盘": [10.0, 10.5],
        "收盘": [10.5, 11.0],
        "最高": [11.0, 11.2],
        "最低": [9.5, 10.2],
        "成交量": [1000000, 1200000],
        "成交额": [1.05e7, 1.3e7],
        "涨跌幅": [1.0, 2.0],  # extra column, should be dropped
    })
    with patch("app.sources.eastmoney.ak.stock_zh_a_hist", return_value=mock_raw):
        from app.sources.eastmoney import EastMoneySource
        df = EastMoneySource().fetch("600519", date(2024,1,1), date(2024,1,31))

    assert list(df.columns) == ["date", "open", "high", "low", "close", "volume", "amount"]
    assert df["date"].dtype == object  # .dt.date returns Python date objects
    assert df["date"].iloc[0] == date(2024, 1, 2)
    for col in ("open", "high", "low", "close", "amount"):
        assert df[col].dtype.kind == "f"
    assert df["volume"].dtype.kind in ("i", "u", "f")
    assert (df["high"] >= df["open"]).all()
    assert (df["high"] >= df["close"]).all()
    assert (df["high"] >= df["low"]).all()
```

- [ ] **Step 6: 运行验证通过**

Run: `pytest tests/test_service.py::test_eastmoney_source_format -v`
Expected: PASS

- [ ] **Step 7: 添加 get_kline 指定 source 优先/回退测试**

```python
@pytest.mark.asyncio
async def test_get_kline_with_source_uses_priority():
    from app.service import get_kline
    from datetime import date

    with (
        patch("app.service.calendar_service.ensure_fresh"),
        patch("app.service.calendar_service.nearest_forward", return_value=date(2024,1,2)),
        patch("app.service.calendar_service.nearest_backward", return_value=date(2024,1,3)),
        patch("app.service.query_cached", return_value=[]),
        patch("app.service.SOURCES", {
            "sina": AsyncMock(),
            "tencent": AsyncMock(),
        }) as mock_sources,
        patch("app.service.upsert_kline"),
    ):
        mock_sources["sina"].fetch = AsyncMock(return_value=pd.DataFrame())
        mock_sources["tencent"].fetch = AsyncMock(return_value=pd.DataFrame(
            {"date": [date(2024,1,2), date(2024,1,3)],
             "open": [10.0, 10.5], "high": [11.0, 11.2], "low": [9.5, 10.2],
             "close": [10.5, 11.0], "volume": [1000000, 1200000], "amount": [1.05e7, 1.3e7]}
        ))

        await get_kline("SH.600519", date(2024,1,1), date(2024,1,31), source="tencent")

        # tencent should be tried first (before sina)
        calls = mock_sources["tencent"].fetch.call_count
        assert calls > 0, "tencent should have been called as the specified source"
```

- [ ] **Step 8: 运行验证通过**

Run: `pytest tests/test_service.py::test_get_kline_with_source_uses_priority -v`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add tests/test_service.py
git commit -m "test: source format validation + get_kline source priority"
```

---

### Task 5: Router 和 kline_sync 测试

**Files:**
- Modify: `tests/test_router.py`
- Modify: `tests/test_kline_sync.py`

- [ ] **Step 1: Router 测试 — 验证 source 参数被接受（集成测试）**

`tests/test_router.py` 末尾新增：
```python
def test_kline_with_source_param():
    resp = client.get("/kline/SH.600519?start=2024-01-01&end=2024-01-03&source=tencent")
    assert resp.status_code == 200
```

（使用现有 `client = TestClient(app)` 模块级 fixture，和已有测试风格一致）

- [ ] **Step 2: 运行验证通过**

Run: `pytest tests/test_router.py::test_kline_with_source_param -v`
Expected: PASS

- [ ] **Step 3: kline_sync 测试 — 验证 source 参透传**

`tests/test_kline_sync.py` 中新增：
```python
@pytest.mark.asyncio
async def test_sync_one_with_source(mock_pool):
    pool, conn = mock_pool
    conn.fetchrow.return_value = {"symbol": "SH.600519"}
    conn.execute.return_value = "UPDATE 1"

    with patch("app.kline_sync.get_kline", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = []
        result = await KlineSyncService().sync_one(pool, source="sina")

    mock_get.assert_called_once_with("SH.600519", Y2000, YESTERDAY, source="sina")
    assert result == 1
```

- [ ] **Step 4: 运行验证通过**

Run: `pytest tests/test_kline_sync.py::test_sync_one_with_source -v`
Expected: PASS

- [ ] **Step 5: 全部测试通过**

Run: `pytest tests/ -v`
Expected: 全部 PASS

- [ ] **Step 6: Commit**

```bash
git add tests/test_router.py tests/test_kline_sync.py
git commit -m "test: source param passthrough for router and kline_sync"
```
