from datetime import date, timedelta
from unittest.mock import MagicMock, patch, AsyncMock
import pandas as pd
import pytest


def _default_start() -> date:
    return date.today() - timedelta(days=30)


def _default_end() -> date:
    return date.today()


@pytest.mark.asyncio
async def test_sina_source_format():
    from src.tools.sources.sina import SinaSource
    df = await SinaSource().fetch("sz000001", _default_start(), _default_end())

    assert not df.empty
    assert list(df.columns) == ["date", "open", "high", "low", "close", "volume", "amount"]
    assert df["date"].dtype.kind in ("M", "O")
    for col in ("open", "high", "low", "close", "amount"):
        assert df[col].dtype.kind == "f", f"{col} dtype={df[col].dtype}"
    assert df["volume"].dtype.kind in ("i", "u", "f")
    assert (df["high"] >= df["low"]).all()


@pytest.mark.asyncio
async def test_tencent_source_format():
    from src.tools.sources.tencent import TencentSource
    try:
        df = await TencentSource().fetch("SZ.000001", _default_start(), _default_end())
    except Exception as e:
        pytest.skip(f"tencent source unavailable: {e}")

    assert not df.empty
    assert list(df.columns) == ["date", "open", "close", "high", "low", "amount", "volume"]
    assert df["volume"].isna().all()
    for col in ("open", "close", "high", "low", "amount"):
        assert df[col].dtype.kind == "f", f"{col} dtype={df[col].dtype}"
    assert (df["high"] >= df["low"]).all()


@pytest.mark.asyncio
async def test_eastmoney_source_format():
    from src.tools.sources.eastmoney import EastMoneySource
    try:
        df = await EastMoneySource().fetch("SZ.000001", _default_start(), _default_end())
    except Exception as e:
        pytest.skip(f"eastmoney source unavailable: {e}")

    assert not df.empty
    assert list(df.columns) == ["date", "open", "high", "low", "close", "volume", "amount"]
    assert df["date"].dtype == object
    assert isinstance(df["date"].iloc[0], date)
    for col in ("open", "high", "low", "close", "amount"):
        assert df[col].dtype.kind == "f", f"{col} dtype={df[col].dtype}"
    assert df["volume"].dtype.kind in ("i", "u", "f")
    assert (df["high"] >= df["low"]).all()


@pytest.mark.asyncio
async def test_mootdx_source_format():
    from src.tools.sources.mootdx import MootdxSource
    try:
        df = await MootdxSource().fetch("SH.600300", _default_start(), _default_end())
    except Exception as e:
        pytest.skip(f"mootdx source unavailable: {e}")

    assert not df.empty
    assert list(df.columns) == ["date", "open", "high", "low", "close", "volume", "amount"]
    assert df["date"].dtype.kind in ("M", "O")
    for col in ("open", "high", "low", "close", "amount"):
        assert df[col].dtype.kind == "f", f"{col} dtype={df[col].dtype}"
    assert df["volume"].dtype.kind in ("i", "u", "f")
    assert (df["high"] >= df["low"]).all()


def test_no_adjust_returns_raw(sample_records):
    from src.services.kline_service import _apply_adjust
    result = _apply_adjust(sample_records, [], {}, "qfq")
    assert result[0].close == 10.5


def test_qfq_adjust_applies_factor(sample_records):
    events = [type("E", (), {"ex_date": date(2024, 6, 1)})()]
    adj_map = {date(2024, 6, 1): 0.85}
    from src.services.kline_service import _apply_adjust
    result = _apply_adjust(sample_records, events, adj_map, "qfq")
    assert result[0].close == pytest.approx(10.5 * 0.85)
    assert result[1].close == pytest.approx(11.0 * 0.85)


@pytest.mark.asyncio
async def test_get_kline_with_source_uses_priority():
    from src.services.kline_service import get_kline

    mock_pool = MagicMock()
    mock_pool.acquire.return_value = AsyncMock()
    mock_pool.acquire.return_value.__aenter__.return_value = AsyncMock()

    with (
        patch("src.services.kline_service.get_pool", return_value=mock_pool),
        patch("src.services.kline_service.calendar_service.ensure_fresh"),
        patch("src.services.kline_service.calendar_service.nearest_forward", return_value=date(2024, 1, 2)),
        patch("src.services.kline_service.calendar_service.nearest_backward", return_value=date(2024, 1, 3)),
        patch("src.services.kline_service.kline_repository.get_cached", return_value=[]),
        patch("src.services.kline_service.SOURCES", {
            "sina": AsyncMock(),
            "tencent": AsyncMock(),
        }) as mock_sources,
        patch("src.services.kline_service.kline_repository.upsert_many"),
    ):
        mock_sources["sina"].fetch = AsyncMock(return_value=pd.DataFrame())
        mock_sources["tencent"].fetch = AsyncMock(return_value=pd.DataFrame(
            {"date": [date(2024, 1, 2), date(2024, 1, 3)],
             "open": [10.0, 10.5], "high": [11.0, 11.2], "low": [9.5, 10.2],
             "close": [10.5, 11.0], "volume": [1000000, 1200000], "amount": [1.05e7, 1.3e7]}
        ))

        await get_kline("SH.600519", date(2024, 1, 1), date(2024, 1, 31), source="tencent")

        calls = mock_sources["tencent"].fetch.call_count
        assert calls > 0, "tencent should have been called as the specified source"


def test_hfq_adjust_applies_factor(sample_records):
    events = [type("E", (), {"ex_date": date(2024, 1, 1)})()]
    adj_map = {date(2024, 1, 1): 0.7}
    from src.services.kline_service import _apply_adjust
    result = _apply_adjust(sample_records, events, adj_map, "hfq")
    assert result[0].close == pytest.approx(10.5 / 0.7)
