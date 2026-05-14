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
