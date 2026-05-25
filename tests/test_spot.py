import pytest
import pandas as pd
from unittest.mock import patch, MagicMock


@pytest.fixture
def mock_akshare():
    data = {
        "代码": ["600519", "000001"],
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
    assert source.name == "eastmoney_spot"


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
    with patch("akshare.stock_zh_a_spot_em", return_value=mock_akshare):
        df = await source.fetch_all()
        assert len(df) == 2
        assert list(df["代码"]) == ["600519", "000001"]


@pytest.mark.asyncio
async def test_spot_source_filter_symbol(mock_akshare):
    from app.sources.spot import SpotSource
    source = SpotSource()
    filtered = source.filter_symbol(mock_akshare, "SH.600519")
    assert len(filtered) == 1
    assert filtered.iloc[0]["代码"] == "600519"


def test_spot_source_filter_symbol_empty():
    from app.sources.spot import SpotSource
    source = SpotSource()
    df = source.filter_symbol(pd.DataFrame({"代码": ["000001"]}), "SH.600519")
    assert len(df) == 0
