from datetime import date
from fastapi.testclient import TestClient
from app.main import app
from app.schemas import CashFlowSheetRecord

client = TestClient(app)


def test_cash_flow_sheet_record_defaults():
    r = CashFlowSheetRecord(
        symbol="SH.600519",
        report_date=date(2024, 3, 31),
        data={"operating_cash_flow": 1.5e11, "free_cash_flow": 7.5e10},
    )
    assert r.symbol == "SH.600519"
    assert r.report_date == date(2024, 3, 31)
    assert r.data["operating_cash_flow"] == 1.5e11
    assert r.data["free_cash_flow"] == 7.5e10


def test_cash_flow_sheet_record_empty_data():
    r = CashFlowSheetRecord(
        symbol="SZ.000001",
        report_date=date(2024, 3, 31),
        data={},
    )
    assert r.data == {}


def test_cash_flow_sheet_route_no_refresh():
    resp = client.get("/cash-flow/SH.600519")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    if data:
        item = data[0]
        assert "symbol" in item
        assert "report_date" in item
        assert "data" in item
