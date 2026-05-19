from datetime import date
from fastapi.testclient import TestClient
from app.main import app
from app.schemas import BalanceSheetRecord

client = TestClient(app)


def test_balance_sheet_record_defaults():
    r = BalanceSheetRecord(
        symbol="SH.600519",
        report_date=date(2024, 3, 31),
        data={"total_assets": 3.5e11, "total_liabilities": 1.2e11},
    )
    assert r.symbol == "SH.600519"
    assert r.report_date == date(2024, 3, 31)
    assert r.data["total_assets"] == 3.5e11
    assert r.data["total_liabilities"] == 1.2e11


def test_balance_sheet_record_empty_data():
    r = BalanceSheetRecord(
        symbol="SZ.000001",
        report_date=date(2024, 3, 31),
        data={},
    )
    assert r.data == {}


def test_balance_sheet_route_no_refresh():
    resp = client.get("/balance/SH.600519")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    if data:
        item = data[0]
        assert "symbol" in item
        assert "report_date" in item
        assert "data" in item
