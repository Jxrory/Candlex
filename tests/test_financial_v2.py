import pytest

TABLE_NAMES = [
    "financial_per_share",
    "financial_balance_sheet",
    "financial_income_sheet",
    "financial_cash_flow",
    "financial_ratio",
    "financial_holdings",
]


def test_financial_tables_has_six_entries():
    from app.financial_v2 import FINANCIAL_TABLES

    assert len(FINANCIAL_TABLES) == 6
    assert FINANCIAL_TABLES == sorted(TABLE_NAMES)


def test_module_exports():
    from app.financial_v2 import __all__

    assert "get_financial_data" in __all__
    assert "query_financial" in __all__


def test_table_columns_importable():
    from app.financial_v2_mapping import TABLE_COLUMNS

    assert isinstance(TABLE_COLUMNS, dict)
    for name in TABLE_NAMES:
        assert name in TABLE_COLUMNS
        cols = TABLE_COLUMNS[name]
        assert len(cols) > 0
        for col in cols:
            assert col.chinese_name
            assert col.english_name


def test_english_to_table_consistent():
    from app.financial_v2_mapping import TABLE_COLUMNS, ENGLISH_TO_TABLE

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
    from app.financial_v2_mapping import TABLE_COLUMNS

    for table_name, cols in TABLE_COLUMNS.items():
        seen = set()
        for col in cols:
            assert col.chinese_name not in seen, (
                f"Duplicate chinese_name '{col.chinese_name}' "
                f"in {table_name}"
            )
            seen.add(col.chinese_name)


def test_last_n_quarter_dates_default_four():
    from app.financial_v2 import _last_n_quarter_dates

    dates = _last_n_quarter_dates(4)
    assert len(dates) == 4
    for d in dates:
        assert d.month in (3, 6, 9, 12)
        assert d.day in (31, 30)


def test_last_n_quarter_dates_returns_descending():
    from app.financial_v2 import _last_n_quarter_dates

    dates = _last_n_quarter_dates(4)
    for i in range(len(dates) - 1):
        assert dates[i] > dates[i + 1]


def test_last_n_quarter_dates_year_boundary():
    from app.financial_v2 import _last_n_quarter_dates
    from datetime import date

    n = 6
    dates = _last_n_quarter_dates(n)
    assert len(dates) == n
    years = {d.year for d in dates}
    assert len(years) >= 2  # crosses at least 2 years


def test_last_n_quarter_dates_all_quarter_ends():
    from app.financial_v2 import _last_n_quarter_dates, _QUARTER_END

    dates = _last_n_quarter_dates(8)
    for d in dates:
        assert (d.month, d.day) in _QUARTER_END.values()


def test_default_report_date_range_covers_four_quarters():
    from app.financial_v2 import _default_report_date_range, _last_n_quarter_dates

    rstart, rend = _default_report_date_range()
    dates = _last_n_quarter_dates(4)
    assert rstart == dates[-1]
    assert rend == dates[0]


def test_default_report_date_range_start_before_end():
    from app.financial_v2 import _default_report_date_range

    rstart, rend = _default_report_date_range()
    assert rstart <= rend


def test_chinese_names_no_obvious_typos():
    from app.financial_v2_mapping import TABLE_COLUMNS

    suspicious = []
    for table_name, cols in TABLE_COLUMNS.items():
        for col in cols:
            name = col.chinese_name
            if "　" in name:
                suspicious.append((table_name, name))
    assert not suspicious, f"Full-width spaces found: {suspicious}"
