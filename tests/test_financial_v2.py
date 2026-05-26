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


def test_financial_v2_service_has_expected_methods():
    from app.financial_v2 import FinancialV2Service

    svc = FinancialV2Service()
    assert hasattr(svc, "get_financial_data")
    assert hasattr(svc, "query_financial")


def test_module_exports():
    from app.financial_v2 import __all__

    assert "financial_v2_service" in __all__
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


def test_chinese_names_no_obvious_typos():
    from app.financial_v2_mapping import TABLE_COLUMNS

    suspicious = []
    for table_name, cols in TABLE_COLUMNS.items():
        for col in cols:
            name = col.chinese_name
            if "　" in name:
                suspicious.append((table_name, name))
    assert not suspicious, f"Full-width spaces found: {suspicious}"
