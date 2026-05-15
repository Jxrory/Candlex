import pytest
from datetime import date
from fastapi.testclient import TestClient
from app.main import app
from app.sources.stock_list import _code_to_exchange
from app.schemas import StockInfoRecord

client = TestClient(app)


def test_code_to_exchange_sh():
    """600xxx and 688xxx codes map to SH."""
    assert _code_to_exchange("600519") == "SH"
    assert _code_to_exchange("601857") == "SH"
    assert _code_to_exchange("603259") == "SH"
    assert _code_to_exchange("688981") == "SH"


def test_code_to_exchange_sz():
    """0xxxxx and 3xxxxx codes map to SZ."""
    assert _code_to_exchange("000001") == "SZ"
    assert _code_to_exchange("002415") == "SZ"
    assert _code_to_exchange("300750") == "SZ"
    assert _code_to_exchange("301188") == "SZ"


def test_code_to_exchange_bj():
    """4xxxxx and 8xxxxx codes map to BJ."""
    assert _code_to_exchange("830799") == "BJ"
    assert _code_to_exchange("430047") == "BJ"
    assert _code_to_exchange("873001") == "BJ"


def test_code_to_exchange_empty_string():
    """Empty string should return BJ (fallback)."""
    assert _code_to_exchange("") == "BJ"


def test_stock_info_record_defaults():
    """StockInfoRecord should have sensible defaults."""
    r = StockInfoRecord(symbol="SH.600519", name="茅台", market="ZH_A")
    assert r.symbol == "SH.600519"
    assert r.name == "茅台"
    assert r.market == "ZH_A"
    assert r.list_date is None
    assert r.list_status is None
    assert r.industry is None
    assert r.sector is None


def test_stock_info_record_full():
    """StockInfoRecord should accept all fields."""
    r = StockInfoRecord(
        symbol="SH.600519",
        name="贵州茅台",
        market="ZH_A",
        list_date=date(2001, 8, 27),
        list_status="L",
        industry="食品饮料",
        sector="白酒",
    )
    assert r.list_date == date(2001, 8, 27)
    assert r.list_status == "L"
    assert r.industry == "食品饮料"
    assert r.sector == "白酒"


def test_stocks_list():
    resp = client.get("/stocks")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    if data:
        item = data[0]
        assert "symbol" in item
        assert "name" in item
        assert "market" in item
