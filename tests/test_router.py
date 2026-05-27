from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_route_returns_200():
    resp = client.get("/kline/SH.600519?start=2024-01-01&end=2024-01-03")
    assert resp.status_code == 200


def test_bad_symbol_format():
    resp = client.get("/kline/INVALID?start=2024-01-01&end=2024-01-03")
    assert resp.status_code == 422


def test_invalid_adjust():
    resp = client.get("/kline/SH.600519?adjust=invalid")
    assert resp.status_code == 422


def test_dividend_endpoint():
    resp = client.get("/dividend/SH.600519")
    assert resp.status_code == 200


def test_dividend_bad_symbol():
    resp = client.get("/dividend/INVALID")
    assert resp.status_code == 422


def test_dividend_date_range():
    resp = client.get("/dividend/SH.600519?start=2023-01-01&end=2023-12-31")
    assert resp.status_code == 200


def test_dividend_refresh():
    resp = client.get("/dividend/SH.600519?refresh=true")
    assert resp.status_code == 200


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


def test_kline_with_source_param():
    resp = client.get("/kline/SH.600519?start=2024-01-01&end=2024-01-03&source=tencent")
    assert resp.status_code == 200
