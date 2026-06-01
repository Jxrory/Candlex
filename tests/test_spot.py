import pytest
import pandas as pd
from unittest.mock import patch, MagicMock, AsyncMock


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
    from src.tools.sources.spot import SpotSource
    source = SpotSource()
    assert source.name == "sina_spot"


def test_spot_source_to_raw_code():
    from src.tools.sources.spot import SpotSource
    source = SpotSource()
    assert source._to_raw_code("SH.600519") == "600519"
    assert source._to_raw_code("SZ.000001") == "000001"
    assert source._to_raw_code("BJ.830799") == "830799"


@pytest.mark.asyncio
async def test_spot_source_fetch_all(mock_akshare):
    from src.tools.sources.spot import SpotSource
    source = SpotSource()
    with patch("akshare.stock_zh_a_spot", return_value=mock_akshare):
        df = await source.fetch_all()
        assert len(df) == 2
        assert list(df["代码"]) == ["sh600519", "sz000001"]


@pytest.mark.asyncio
async def test_spot_source_filter_symbol(mock_akshare):
    from src.tools.sources.spot import SpotSource
    source = SpotSource()
    filtered = source.filter_symbol(mock_akshare, "SH.600519")
    assert len(filtered) == 1
    assert filtered.iloc[0]["代码"] == "sh600519"


def test_spot_source_filter_symbol_empty():
    from src.tools.sources.spot import SpotSource
    source = SpotSource()
    df = source.filter_symbol(pd.DataFrame({"代码": ["000001"]}), "SH.600519")
    assert len(df) == 0


# ── SpotService tests ──────────────────────────────────────────

from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import json
import pytest


@pytest.mark.asyncio
async def test_spot_service_fetch_real_all(mock_akshare):
    from src.services.spot_service import SpotService
    service = SpotService()
    with patch("akshare.stock_zh_a_spot", return_value=mock_akshare):
        result = await service.fetch_real()
    assert len(result) == 2
    assert result[0]["代码"] == "sh600519"


@pytest.mark.asyncio
async def test_spot_service_fetch_real_symbol(mock_akshare):
    from src.services.spot_service import SpotService
    service = SpotService()
    with patch("akshare.stock_zh_a_spot", return_value=mock_akshare):
        result = await service.fetch_real("SH.600519")
    assert len(result) == 1
    assert result[0]["代码"] == "sh600519"


@pytest.mark.asyncio
async def test_spot_service_get_latest_all():
    from src.services.spot_service import SpotService
    from src.repositories.spot_repository import spot_repository
    service = SpotService()
    rows = [
        {"symbol": "SH.600519", "data": json.dumps({"代码": "600519", "最新价": 1800.0, "名称": "贵州茅台"})},
        {"symbol": "SZ.000001", "data": json.dumps({"代码": "000001", "最新价": 12.5, "名称": "平安银行"})},
    ]
    session = AsyncMock()
    with patch.object(spot_repository, "get_all_latest", return_value=rows):
        result = await service.get_latest(session)
    assert len(result) == 2
    assert result[0]["symbol"] == "SH.600519"


@pytest.mark.asyncio
async def test_spot_service_get_latest_symbol():
    from src.services.spot_service import SpotService
    from src.repositories.spot_repository import spot_repository
    service = SpotService()
    session = AsyncMock()
    expected = {"代码": "600519", "最新价": 1800.0}
    with patch.object(spot_repository, "get_latest_by_symbol", return_value=expected):
        result = await service.get_latest(session, "SH.600519")
    assert len(result) == 1
    assert result[0]["代码"] == "600519"


@pytest.mark.asyncio
async def test_spot_service_get_latest_no_data():
    from src.services.spot_service import SpotService
    from src.repositories.spot_repository import spot_repository
    service = SpotService()
    session = AsyncMock()
    with patch.object(spot_repository, "get_all_latest", return_value=[]):
        result = await service.get_latest(session)
    assert result == []


@pytest.mark.asyncio
async def test_spot_service_sync_all(mock_akshare):
    from src.services.spot_service import SpotService
    from src.repositories.spot_repository import spot_repository
    from src.repositories.kline_repository import kline_repository
    service = SpotService()
    session = AsyncMock()
    with (
        patch("akshare.stock_zh_a_spot", return_value=mock_akshare),
        patch("src.services.spot_service.datetime") as mock_dt,
        patch.object(spot_repository, "upsert_many"),
        patch.object(kline_repository, "upsert_many"),
    ):
        mock_dt.now.return_value = datetime(2026, 5, 25, 17, 0, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
        count = await service.sync_all(session)
    assert count == 2


# ── Route tests ─────────────────────────────────────────────

from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


def test_spot_real_route_all():
    with patch("src.services.spot_service.spot_service.fetch_real", return_value=[{"代码": "600519", "最新价": 1800.0}]):
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
    with patch("src.services.spot_service.spot_service.fetch_real", return_value=records):
        resp = client.get("/quote/spot/real?codes=600519")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["代码"] == "600519"


def test_spot_real_route_symbol():
    with patch("src.services.spot_service.spot_service.fetch_real", return_value=[{"代码": "600519", "最新价": 1800.0}]):
        resp = client.get("/quote/spot/real/SH.600519")
    assert resp.status_code == 200


def test_spot_real_route_invalid_symbol():
    resp = client.get("/quote/spot/real/INVALID")
    assert resp.status_code == 422


def test_spot_route_all():
    with patch("src.services.spot_service.spot_service.get_latest", return_value=[{"代码": "600519", "最新价": 1800.0}]):
        resp = client.get("/quote/spot")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1


def test_spot_route_symbol():
    with patch("src.services.spot_service.spot_service.get_latest", return_value=[{"代码": "600519", "最新价": 1800.0}]):
        resp = client.get("/quote/spot/SH.600519")
    assert resp.status_code == 200
