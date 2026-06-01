import pytest
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.kline_sync_service import KlineSyncService

Y2000 = date(2000, 1, 1)
TODAY = date.today()
YESTERDAY = TODAY - timedelta(days=1)


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.execute.return_value = MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[]))))
    return session


@pytest.mark.asyncio
async def test_sync_one_success(mock_session):
    session = mock_session

    with patch("src.services.kline_sync_service.get_kline", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = []

        with patch("src.services.kline_sync_service.stock_list_repository.get_next_pending", new_callable=AsyncMock) as mock_pending:
            mock_pending.return_value = "SH.600519"

            with patch("src.services.kline_sync_service.stock_list_repository.mark_synced", new_callable=AsyncMock) as mock_mark:
                result = await KlineSyncService().sync_one(session)

    mock_get.assert_called_once_with(session, "SH.600519", Y2000, YESTERDAY, source=None)
    assert result == 1


@pytest.mark.asyncio
async def test_sync_one_no_pending(mock_session):
    session = mock_session

    with patch("src.services.kline_sync_service.get_kline", new_callable=AsyncMock) as mock_get:
        with patch("src.services.kline_sync_service.stock_list_repository.get_next_pending", new_callable=AsyncMock) as mock_pending:
            mock_pending.return_value = None
            result = await KlineSyncService().sync_one(session)

    mock_get.assert_not_called()
    assert result == 0


@pytest.mark.asyncio
async def test_sync_one_failure(mock_session):
    session = mock_session

    with patch("src.services.kline_sync_service.get_kline", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = Exception("network error")

        with patch("src.services.kline_sync_service.stock_list_repository.get_next_pending", new_callable=AsyncMock) as mock_pending:
            mock_pending.return_value = "SH.600519"

            with patch("src.services.kline_sync_service.stock_list_repository.mark_synced", new_callable=AsyncMock) as mock_mark:
                result = await KlineSyncService().sync_one(session)

    mock_get.assert_called_once_with(session, "SH.600519", Y2000, YESTERDAY, source=None)
    assert result == 0


@pytest.mark.asyncio
async def test_sync_one_with_source(mock_session):
    session = mock_session

    with patch("src.services.kline_sync_service.get_kline", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = []

        with patch("src.services.kline_sync_service.stock_list_repository.get_next_pending", new_callable=AsyncMock) as mock_pending:
            mock_pending.return_value = "SH.600519"

            result = await KlineSyncService().sync_one(session, source="sina")

    mock_get.assert_called_once_with(session, "SH.600519", Y2000, YESTERDAY, source="sina")
    assert result == 1


@pytest.mark.asyncio
async def test_sync_one_selects_any_pending(mock_session):
    session = mock_session

    with patch("src.services.kline_sync_service.get_kline", new_callable=AsyncMock) as mock_get:
        with patch("src.services.kline_sync_service.stock_list_repository.get_next_pending", new_callable=AsyncMock) as mock_pending:
            mock_pending.return_value = None
            await KlineSyncService().sync_one(session)

    mock_pending.assert_called_once_with(session)
