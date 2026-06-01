import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock

from src.database import get_db
from src.main import app


@pytest.fixture
def sample_kline_records():
    return [
        {"date": date(2024, 1, 2), "open": 10.0, "high": 11.0, "low": 9.5,
         "close": 10.5, "volume": 1000000, "amount": 1.05e7},
        {"date": date(2024, 1, 3), "open": 10.5, "high": 11.2, "low": 10.2,
         "close": 11.0, "volume": 1200000, "amount": 1.3e7},
    ]


@pytest.fixture
def sample_records(sample_kline_records):
    from src.schemas.schemas import KlineRecord
    return [KlineRecord(**r) for r in sample_kline_records]


@pytest.fixture(autouse=True)
def mock_db_session():
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_result.one_or_none.return_value = None
    mock_result.first.return_value = None
    session = AsyncMock()
    session.execute.return_value = mock_result
    session.get.return_value = None
    app.dependency_overrides[get_db] = lambda: session
    yield
    app.dependency_overrides.pop(get_db, None)
