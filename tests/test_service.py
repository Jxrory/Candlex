from datetime import date
import pytest


def test_no_adjust_returns_raw(sample_records):
    from app.service import _apply_adjust
    result = _apply_adjust(sample_records, [], {}, "qfq")
    assert result[0].close == 10.5


def test_qfq_adjust_applies_factor(sample_records):
    events = [type("E", (), {"ex_date": date(2024, 6, 1)})()]
    adj_map = {date(2024, 6, 1): 0.85}
    from app.service import _apply_adjust
    result = _apply_adjust(sample_records, events, adj_map, "qfq")
    assert result[0].close == pytest.approx(10.5 * 0.85)
    assert result[1].close == pytest.approx(11.0 * 0.85)


def test_hfq_adjust_applies_factor(sample_records):
    events = [type("E", (), {"ex_date": date(2024, 1, 1)})()]
    adj_map = {date(2024, 1, 1): 0.7}
    from app.service import _apply_adjust
    result = _apply_adjust(sample_records, events, adj_map, "hfq")
    assert result[0].close == pytest.approx(10.5 / 0.7)
