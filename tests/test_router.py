from datetime import date
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


@patch("src.routers.kline_router.get_kline", return_value=[])
def test_route_returns_200(mock_kline):
    resp = client.get("/kline/SH.600519?start=2024-01-01&end=2024-01-03")
    assert resp.status_code == 200


def test_bad_symbol_format():
    resp = client.get("/kline/INVALID?start=2024-01-01&end=2024-01-03")
    assert resp.status_code == 422


def test_invalid_adjust():
    resp = client.get("/kline/SH.600519?adjust=invalid")
    assert resp.status_code == 422


@patch("src.routers.dividend_router.dividend_service.get_events", return_value=[])
def test_dividend_endpoint(mock_events):
    resp = client.get("/dividend/SH.600519")
    assert resp.status_code == 200


def test_dividend_bad_symbol():
    resp = client.get("/dividend/INVALID")
    assert resp.status_code == 422


@patch("src.routers.dividend_router.dividend_service.get_events", return_value=[])
def test_dividend_date_range(mock_events):
    resp = client.get("/dividend/SH.600519?start=2023-01-01&end=2023-12-31")
    assert resp.status_code == 200


@patch("src.routers.dividend_router.dividend_service.sync_symbol", return_value=0)
@patch("src.routers.dividend_router.dividend_service.get_events", return_value=[])
def test_dividend_refresh(mock_events, mock_sync):
    resp = client.get("/dividend/SH.600519?refresh=true")
    assert resp.status_code == 200


@patch("src.routers.kline_router.get_indicators", return_value=[])
def test_indicators_basic(mock_indicators):
    resp = client.get("/indicators/SH.600519?start=2024-01-01&end=2024-01-10&i=ma:5")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


@patch("src.routers.kline_router.get_indicators", return_value=[])
def test_indicators_multiple(mock_indicators):
    resp = client.get("/indicators/SH.600519?start=2024-01-01&end=2024-01-10&i=ma:5&i=ma:10&i=macd")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


@patch("src.routers.kline_router.get_indicators", return_value=[])
def test_indicators_no_i_returns_raw_kline(mock_indicators):
    resp = client.get("/indicators/SH.600519?start=2024-01-01&end=2024-01-10")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


def test_indicators_bad_symbol():
    resp = client.get("/indicators/INVALID?i=ma:5")
    assert resp.status_code == 422


def test_indicators_unknown_indicator():
    resp = client.get("/indicators/SH.600519?i=unknown:5")
    assert resp.status_code == 422


def test_indicators_invalid_adjust():
    resp = client.get("/indicators/SH.600519?adjust=bad&i=ma:5")
    assert resp.status_code == 422


@patch("src.routers.kline_router.get_indicators", return_value=[])
def test_indicators_with_adjust(mock_indicators):
    resp = client.get("/indicators/SH.600519?start=2024-01-01&end=2024-01-10&adjust=qfq&i=ma:5")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


@patch("src.routers.kline_router.get_kline", return_value=[])
def test_kline_with_source_param(mock_kline):
    resp = client.get("/kline/SH.600519?start=2024-01-01&end=2024-01-03&source=tencent")
    assert resp.status_code == 200
