import pytest
from datetime import date


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
    from app.service import _rows_to_records
    return _rows_to_records(sample_kline_records)
