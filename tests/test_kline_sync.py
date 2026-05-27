import pytest
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.kline_sync import KlineSyncService

Y2000 = date(2000, 1, 1)
TODAY = date.today()
YESTERDAY = TODAY - timedelta(days=1)


@pytest.mark.asyncio
async def test_sync_all_success():
    pool = MagicMock()
    conn = AsyncMock()
    pool.acquire.return_value.__aenter__.return_value = conn
    conn.fetch.return_value = [{"symbol": "SH.600519"}]
    conn.execute.return_value = "UPDATE 1"

    with patch("app.kline_sync.get_kline", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = []
        result = await KlineSyncService().sync_all(pool)

    mock_get.assert_called_once_with("SH.600519", Y2000, YESTERDAY)
    conn.execute.assert_called_once_with(
        "UPDATE stock_info SET list_status = 'SYNCED', list_date = NOW() WHERE symbol = $1",
        "SH.600519",
    )
    assert result == 1


@pytest.mark.asyncio
async def test_no_pending_stocks():
    pool = MagicMock()
    conn = AsyncMock()
    pool.acquire.return_value.__aenter__.return_value = conn
    conn.fetch.return_value = []

    with patch("app.kline_sync.get_kline", new_callable=AsyncMock) as mock_get:
        result = await KlineSyncService().sync_all(pool)

    mock_get.assert_not_called()
    assert result == 0


@pytest.mark.asyncio
async def test_failure_skips_and_continues():
    pool = MagicMock()
    conn = AsyncMock()
    pool.acquire.return_value.__aenter__.return_value = conn
    conn.fetch.return_value = [
        {"symbol": "SH.600519"},
        {"symbol": "SZ.000001"},
    ]
    conn.execute.return_value = "UPDATE 1"

    with patch("app.kline_sync.get_kline", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = [Exception("network error"), []]
        result = await KlineSyncService().sync_all(pool)

    assert mock_get.call_count == 2
    conn.execute.assert_called_once_with(
        "UPDATE stock_info SET list_status = 'SYNCED', list_date = NOW() WHERE symbol = $1",
        "SZ.000001",
    )
    assert result == 1


@pytest.mark.asyncio
async def test_only_sz_sh():
    pool = MagicMock()
    conn = AsyncMock()
    pool.acquire.return_value.__aenter__.return_value = conn
    conn.fetch.return_value = [
        {"symbol": "SH.600519"},
        {"symbol": "SZ.000001"},
        {"symbol": "SZ.300750"},
    ]
    conn.execute.return_value = "UPDATE 1"

    with patch("app.kline_sync.get_kline", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = []
        await KlineSyncService().sync_all(pool)

    conn.fetch.assert_called_once()
    sql = conn.fetch.call_args[0][0]
    assert "LIKE 'SH.%'" in sql or "LIKE 'SZ.%'" in sql
    assert "LIKE 'BJ.%'" not in sql
