import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from datetime import date

TABLE_NAMES = [
    "financial_per_share",
    "financial_balance_sheet",
    "financial_income_sheet",
    "financial_cash_flow",
    "financial_ratio",
    "financial_holdings",
]


def test_financial_tables_has_six_entries():
    from src.services.financial_service import FINANCIAL_TABLES

    assert len(FINANCIAL_TABLES) == 6
    assert FINANCIAL_TABLES == sorted(TABLE_NAMES)


def test_module_exports():
    from src.services.financial_service import __all__

    assert "get_financial_data" in __all__
    assert "query_financial" in __all__


def test_table_columns_importable():
    from src.models.financial_mapping import TABLE_COLUMNS

    assert isinstance(TABLE_COLUMNS, dict)
    for name in TABLE_NAMES:
        assert name in TABLE_COLUMNS
        cols = TABLE_COLUMNS[name]
        assert len(cols) > 0
        for col in cols:
            assert col.chinese_name
            assert col.english_name


def test_english_to_table_consistent():
    from src.models.financial_mapping import TABLE_COLUMNS, ENGLISH_TO_TABLE

    assert isinstance(ENGLISH_TO_TABLE, dict)

    all_english = set()
    for table_name, cols in TABLE_COLUMNS.items():
        for col in cols:
            assert (
                col.english_name in ENGLISH_TO_TABLE
            ), f"{col.english_name} from {table_name} missing in ENGLISH_TO_TABLE"
            assert (
                ENGLISH_TO_TABLE[col.english_name] == table_name
            ), f"{col.english_name} maps to wrong table"
            all_english.add(col.english_name)

    assert len(ENGLISH_TO_TABLE) == len(all_english)


def test_chinese_names_unique_within_each_table():
    from src.models.financial_mapping import TABLE_COLUMNS

    for table_name, cols in TABLE_COLUMNS.items():
        seen = set()
        for col in cols:
            assert col.chinese_name not in seen, (
                f"Duplicate chinese_name '{col.chinese_name}' "
                f"in {table_name}"
            )
            seen.add(col.chinese_name)


def test_last_n_quarter_dates_default_four():
    from src.services.financial_service import _last_n_quarter_dates

    dates = _last_n_quarter_dates(4)
    assert len(dates) == 4
    for d in dates:
        assert d.month in (3, 6, 9, 12)
        assert d.day in (31, 30)


def test_last_n_quarter_dates_returns_descending():
    from src.services.financial_service import _last_n_quarter_dates

    dates = _last_n_quarter_dates(4)
    for i in range(len(dates) - 1):
        assert dates[i] > dates[i + 1]


def test_last_n_quarter_dates_year_boundary():
    from src.services.financial_service import _last_n_quarter_dates

    n = 6
    dates = _last_n_quarter_dates(n)
    assert len(dates) == n
    years = {d.year for d in dates}
    assert len(years) >= 2


def test_last_n_quarter_dates_all_quarter_ends():
    from src.services.financial_service import _last_n_quarter_dates, _QUARTER_END

    dates = _last_n_quarter_dates(8)
    for d in dates:
        assert (d.month, d.day) in _QUARTER_END.values()


def test_default_report_date_range_covers_four_quarters():
    from src.services.financial_service import _default_report_date_range, _last_n_quarter_dates

    rstart, rend = _default_report_date_range()
    dates = _last_n_quarter_dates(4)
    assert rstart == dates[-1]
    assert rend == dates[0]


def test_default_report_date_range_start_before_end():
    from src.services.financial_service import _default_report_date_range

    rstart, rend = _default_report_date_range()
    assert rstart <= rend


# ── Concurrent query guard tests ──────────────────────────────────


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return _FakeScalars(self._rows)

    def all(self):
        return self._rows

    def __iter__(self):
        return iter(self._rows)

    def one_or_none(self):
        return self._rows[0] if self._rows else None

    def scalar(self):
        return self._rows[0] if self._rows else None


class _FakeScalars:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


@pytest.mark.asyncio
async def test_get_symbol_data_rejects_concurrent_queries():
    """Verifies that get_symbol_data does not use asyncio.gather on the same session."""
    from src.repositories.financial_repository import financial_repository
    from src.models.financial import FinancialRatio

    row = FinancialRatio(
        symbol="SH.600000",
        report_date=date(2025, 6, 30),
        roe=15.0,
    )

    session = AsyncMock()
    result_for_table = _FakeResult([row])
    session.execute.return_value = result_for_table

    results = await financial_repository.get_symbol_data(session, "SH.600000")
    assert len(results) == 1
    assert results[0]["symbol"] == "SH.600000"
    assert results[0]["report_date"] == date(2025, 6, 30)


@pytest.mark.asyncio
async def test_query_financial_rejects_concurrent_queries():
    """Same exclusive-access check for the query_financial code path."""
    from src.services.financial_service import query_financial
    from src.models.financial import FinancialRatio
    from src.models.financial_mapping import TABLE_COLUMNS

    row = FinancialRatio(
        symbol="SH.600000",
        report_date=date(2025, 6, 30),
    )

    session = AsyncMock()
    session.execute.return_value = _FakeResult([row])

    cols = TABLE_COLUMNS["financial_ratio"]
    filters = {cols[0].english_name: (0.5, 1.5)}
    results = await query_financial(
        session, filters,
        report_date_start=date(2025, 1, 1),
        report_date_end=date(2025, 12, 31),
    )
    assert "SH.600000" in results


# ── Regression: renamed ORM columns ─────────────────────────


@pytest.mark.asyncio
async def test_fetch_symbol_rows_handles_mapped_column_names():
    """fetch_symbol_rows must use ORM attribute keys, not DB column names.

    Regression: FinancialPerShare has weight_roe mapped to DB column
    'weighted_roe'.  Iterating __table__.columns and calling
    getattr(row, col.name) fails because 'weighted_roe' is not the
    Python attribute name.
    """
    from src.repositories.financial_repository import financial_repository
    from src.models.financial import FinancialPerShare

    row = FinancialPerShare(
        symbol="SH.600519",
        report_date=date(2024, 6, 30),
        weight_roe=15.5,
        eps=2.5,
    )

    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [row]
    session.execute.return_value = mock_result

    rows = await financial_repository.fetch_symbol_rows(
        session, "financial_per_share", "SH.600519", [date(2024, 6, 30)]
    )
    assert len(rows) == 1
    assert rows[0]["weight_roe"] == 15.5
    assert rows[0]["eps"] == 2.5


@pytest.mark.asyncio
async def test_get_symbol_data_handles_mapped_column_names():
    """Same issue in get_symbol_data: must not use getattr(row, col.name)."""
    from src.repositories.financial_repository import financial_repository
    from src.models.financial import FinancialPerShare

    row = FinancialPerShare(
        symbol="SH.600519",
        report_date=date(2024, 6, 30),
        weight_roe=15.5,
        eps=2.5,
    )

    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [row]
    session.execute.return_value = mock_result

    rows = await financial_repository.get_symbol_data(session, "SH.600519")
    assert len(rows) == 1
    assert rows[0]["weight_roe"] == 15.5
    assert rows[0]["eps"] == 2.5


def test_chinese_names_no_obvious_typos():
    from src.models.financial_mapping import TABLE_COLUMNS

    suspicious = []
    for table_name, cols in TABLE_COLUMNS.items():
        for col in cols:
            name = col.chinese_name
            if "　" in name:
                suspicious.append((table_name, name))
    assert not suspicious, f"Full-width spaces found: {suspicious}"
