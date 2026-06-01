import asyncio
import json
import logging
from datetime import date
import pytest
from src.services.ak_trace import trace_akshare, _extract_symbol, _extract_params


class TestExtractSymbol:
    def test_from_kwargs(self):
        assert _extract_symbol("stock_zh_a_daily", (), {"symbol": "SH.600519"}) == "SH.600519"

    def test_from_positional(self):
        assert _extract_symbol("stock_zh_a_daily", ("SH.600519",), {}) == "SH.600519"

    def test_from_digit_code(self):
        assert _extract_symbol("stock_history_dividend_detail", ("000001",), {}) == "000001"

    def test_none_when_no_match(self):
        assert _extract_symbol("test_api", ("hello",), {}) is None


class TestExtractParams:
    def test_kwargs_passthrough(self):
        params = _extract_params("stock_zh_a_daily", (), {"start_date": "20240101"})
        assert params["start_date"] == "20240101"

    def test_api_with_indicator(self):
        params = _extract_params("stock_history_dividend_detail", (), {"indicator": "分红"})
        assert params["indicator"] == "分红"


class TestTraceDecorator:
    async def test_successful_call(self):
        @trace_akshare("test_api")
        async def dummy():
            return [1, 2, 3]

        result = await dummy()
        assert result == [1, 2, 3]

    async def test_exception_raised(self):
        @trace_akshare("test_api")
        async def failing():
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError, match="boom"):
            await failing()

    async def test_sync_function_supported(self):
        @trace_akshare("test_sync")
        def sync_dummy():
            return "ok"

        result = await sync_dummy()
        assert result == "ok"

    async def test_queue_dropped_when_not_started(self):
        from src.services.ak_trace import _schedule_pg_insert
        _schedule_pg_insert("test", None, {}, "success", 1, 100, None)
