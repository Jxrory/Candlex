import pytest
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.kline_sync import KlineSyncService

Y2000 = date(2000, 1, 1)
TODAY = date.today()
YESTERDAY = TODAY - timedelta(days=1)


@pytest.fixture
def mock_pool():
    pool = MagicMock()
    conn = AsyncMock()
    pool.acquire.return_value.__aenter__.return_value = conn
    return pool, conn


@pytest.mark.asyncio
async def test_sync_one_success(mock_pool):
    pool, conn = mock_pool
    conn.fetchrow.return_value = {"symbol": "SH.600519"}
    conn.execute.return_value = "UPDATE 1"

    with patch("app.kline_sync.get_kline", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = []
        result = await KlineSyncService().sync_one(pool)

    mock_get.assert_called_once_with("SH.600519", Y2000, YESTERDAY)
    conn.execute.assert_called_once_with(
        "UPDATE stock_info SET list_status = 'SYNCED', list_date = NOW() WHERE symbol = $1",
        "SH.600519",
    )
    assert result == 1


@pytest.mark.asyncio
async def test_sync_one_no_pending(mock_pool):
    pool, conn = mock_pool
    conn.fetchrow.return_value = None

    with patch("app.kline_sync.get_kline", new_callable=AsyncMock) as mock_get:
        result = await KlineSyncService().sync_one(pool)

    mock_get.assert_not_called()
    assert result == 0


@pytest.mark.asyncio
async def test_sync_one_failure(mock_pool):
    pool, conn = mock_pool
    conn.fetchrow.return_value = {"symbol": "SH.600519"}
    conn.execute.return_value = "UPDATE 1"

    with patch("app.kline_sync.get_kline", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = Exception("network error")
        result = await KlineSyncService().sync_one(pool)

    mock_get.assert_called_once_with("SH.600519", Y2000, YESTERDAY)
    conn.execute.assert_not_called()
    assert result == 0


@pytest.mark.asyncio
async def test_sync_one_only_sz_sh(mock_pool):
    pool, conn = mock_pool
    conn.fetchrow.return_value = None

    await KlineSyncService().sync_one(pool)

    conn.fetchrow.assert_called_once()
    sql = conn.fetchrow.call_args[0][0]
    assert "LIKE 'SH.%'" in sql
    assert "LIKE 'SZ.%'" in sql
    assert "LIKE 'BJ.%'" not in sql
    assert "LIMIT 1" in sql
