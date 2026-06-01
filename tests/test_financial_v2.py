import asyncio

import asyncpg
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
    from datetime import date

    n = 6
    dates = _last_n_quarter_dates(n)
    assert len(dates) == n
    years = {d.year for d in dates}
    assert len(years) >= 2  # crosses at least 2 years


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


# ── Concurrent connection guard ──────────────────────────────────


class _FakeConn:
    """Emulates asyncpg's exclusive-access enforcement.

    Raises ``InterfaceError('cannot perform operation: another operation is in progress')``
    if a second ``fetch`` starts before the first completes.
    Ignores SQL parameters — returns all rows for the matched table.
    """

    def __init__(self, table_data: dict[str, list[dict]]):
        self._table_data = table_data
        self._query_in_progress = False

    async def fetch(self, query: str, *params) -> list[dict]:
        if self._query_in_progress:
            msg = "cannot perform operation: another operation is in progress"
            raise asyncpg.InterfaceError(msg)
        self._query_in_progress = True
        try:
            await asyncio.sleep(0)
            for name in TABLE_NAMES:
                if name in query:
                    return self._table_data.get(name, [])
            return []
        finally:
            self._query_in_progress = False

    async def fetchrow(self, query: str, *params):
        rows = await self.fetch(query, *params)
        return rows[0] if rows else None

    async def executemany(self, query: str, rows):
        self._table_data = {}
        return len(rows)


@pytest.mark.asyncio
async def test_get_symbol_data_rejects_concurrent_queries():
    """Verifies that get_symbol_data does not use asyncio.gather on the same connection.

    asyncpg connections raise ``InterfaceError`` when a second query starts
    before the first finishes.  The current code must run table queries
    sequentially.
    """
    from src.repositories.financial_repository import financial_repository

    row = {
        "symbol": "SH.600000",
        "report_date": date(2025, 6, 30),
        "source": "test",
        "updated_at": "2025-01-01",
    }
    table_data = {t: [dict(row, **{t: 1.0})] for t in TABLE_NAMES}

    conn = _FakeConn(table_data)
    results = await financial_repository.get_symbol_data(conn, "SH.600000")
    assert len(results) == 1
    assert results[0]["symbol"] == "SH.600000"
    assert results[0]["report_date"] == date(2025, 6, 30)


@pytest.mark.asyncio
async def test_query_financial_rejects_concurrent_queries():
    """Same exclusive-access check for the query_financial code path."""
    from src.services.financial_service import query_financial
    from src.models.financial_mapping import TABLE_COLUMNS

    row = {
        "symbol": "SH.600000",
        "report_date": date(2025, 6, 30),
    }
    cols = TABLE_COLUMNS["financial_ratio"]
    for c in cols:
        row[c.english_name] = 1.0

    table_data = {"financial_ratio": [dict(row)]}
    conn = _FakeConn(table_data)
    filters = {cols[0].english_name: (0.5, 1.5)}
    results = await query_financial(
        conn, filters,
        report_date_start=date(2025, 1, 1),
        report_date_end=date(2025, 12, 31),
    )
    assert "SH.600000" in results


def test_chinese_names_no_obvious_typos():
    from src.models.financial_mapping import TABLE_COLUMNS

    suspicious = []
    for table_name, cols in TABLE_COLUMNS.items():
        for col in cols:
            name = col.chinese_name
            if "　" in name:
                suspicious.append((table_name, name))
    assert not suspicious, f"Full-width spaces found: {suspicious}"
