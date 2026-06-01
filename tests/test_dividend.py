from datetime import date
import pytest
from src.services.dividend_service import _adjustment_ratio, compute_factor


class TestAdjustmentRatio:
    def test_cash_dividend_only(self):
        adj = _adjustment_ratio(
            prev_close=10.0, cash_dividend=0.5,
            stock_dividend=0.0, capitalization=0.0,
            rights_ratio=0.0, rights_price=None,
        )
        expected = round((10.0 - 0.5) / 10.0, 6)
        assert adj == expected

    def test_stock_dividend_only(self):
        adj = _adjustment_ratio(
            prev_close=10.0, cash_dividend=0.0,
            stock_dividend=0.3, capitalization=0.0,
            rights_ratio=0.0, rights_price=None,
        )
        expected = round(10.0 / (10.0 * 1.3), 6)
        assert adj == expected

    def test_combined_dividend_rights(self):
        adj = _adjustment_ratio(
            prev_close=10.0, cash_dividend=0.2,
            stock_dividend=0.1, capitalization=0.2,
            rights_ratio=0.15, rights_price=8.0,
        )
        C, D, Rs, Rc, Rr, Pr = 10.0, 0.2, 0.1, 0.2, 0.15, 8.0
        expected = round((C + Pr * Rr - D) / (C * (1 + Rs + Rc + Rr)), 6)
        assert adj == expected

    def test_no_events(self):
        adj = _adjustment_ratio(
            prev_close=10.0, cash_dividend=0.0,
            stock_dividend=0.0, capitalization=0.0,
            rights_ratio=0.0, rights_price=None,
        )
        assert adj == 1.0

    def test_zero_denominator_returns_one(self):
        adj = _adjustment_ratio(
            prev_close=0.0, cash_dividend=0.5,
            stock_dividend=0.0, capitalization=0.0,
            rights_ratio=0.0, rights_price=None,
        )
        assert adj == 1.0


class TestComputeFactor:
    def test_qfq_before_all_events(self):
        pairs = [
            (date(2023, 6, 1), 0.95),
            (date(2024, 6, 1), 0.92),
        ]
        factor = compute_factor(pairs, date(2020, 1, 1), "qfq")
        assert factor == pytest.approx(0.95 * 0.92)

    def test_qfq_after_all_events(self):
        pairs = [
            (date(2023, 6, 1), 0.95),
            (date(2024, 6, 1), 0.92),
        ]
        factor = compute_factor(pairs, date(2025, 1, 1), "qfq")
        assert factor == 1.0

    def test_hfq_after_all_events(self):
        pairs = [
            (date(2023, 6, 1), 0.95),
            (date(2024, 6, 1), 0.92),
        ]
        factor = compute_factor(pairs, date(2025, 1, 1), "hfq")
        assert factor == pytest.approx(1.0 / (0.95 * 0.92))

    def test_hfq_before_all_events(self):
        pairs = [
            (date(2023, 6, 1), 0.95),
        ]
        factor = compute_factor(pairs, date(2020, 1, 1), "hfq")
        assert factor == 1.0

    def test_no_events(self):
        factor = compute_factor([], date(2023, 1, 1), "qfq")
        assert factor == 1.0
