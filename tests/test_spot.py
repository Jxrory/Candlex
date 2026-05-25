import pytest
import pandas as pd
from unittest.mock import patch, MagicMock


@pytest.fixture
def mock_akshare():
    data = {
        "代码": ["sh600519", "sz000001"],
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
    assert source.name == "sina_spot"


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
    with patch("akshare.stock_zh_a_spot", return_value=mock_akshare):
        df = await source.fetch_all()
        assert len(df) == 2
        assert list(df["代码"]) == ["sh600519", "sz000001"]


@pytest.mark.asyncio
async def test_spot_source_filter_symbol(mock_akshare):
    from app.sources.spot import SpotSource
    source = SpotSource()
    filtered = source.filter_symbol(mock_akshare, "SH.600519")
    assert len(filtered) == 1
    assert filtered.iloc[0]["代码"] == "sh600519"


def test_spot_source_filter_symbol_empty():
    from app.sources.spot import SpotSource
    source = SpotSource()
    df = source.filter_symbol(pd.DataFrame({"代码": ["000001"]}), "SH.600519")
    assert len(df) == 0


# ── SpotService tests ──────────────────────────────────────────

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
    with patch("akshare.stock_zh_a_spot", return_value=mock_akshare):
        result = await service.fetch_real()
    assert len(result) == 2
    assert result[0]["代码"] == "sh600519"


@pytest.mark.asyncio
async def test_spot_service_fetch_real_symbol(mock_akshare):
    from app.spot import SpotService
    service = SpotService()
    with patch("akshare.stock_zh_a_spot", return_value=mock_akshare):
        result = await service.fetch_real("SH.600519")
    assert len(result) == 1
    assert result[0]["代码"] == "sh600519"


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
    with patch("akshare.stock_zh_a_spot", return_value=mock_akshare):
        with patch("app.spot.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 5, 25, 17, 0, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
            count = await service.sync_all(pool)
    assert count == 2
    assert len(pool.rows) == 2
    assert pool.rows[0][0] == "SH.600519"  # symbol


# ── Route tests ─────────────────────────────────────────────

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
