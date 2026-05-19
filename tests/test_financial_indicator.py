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
