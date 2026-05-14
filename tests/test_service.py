import pytest
from app.service import _apply_adjust


def test_no_adjust_returns_raw(sample_records):
    result = _apply_adjust(sample_records, None)
    assert result[0].close == 10.5


def test_qfq_adjust_applies_factor(sample_records):
    result = _apply_adjust(sample_records, "qfq")
    assert result[0].close == 10.5  # factor_qfq=1.0


def test_hfq_adjust_applies_factor(sample_records):
    result = _apply_adjust(sample_records, "hfq")
    assert result[0].close == pytest.approx(15.75)  # 10.5 * 1.5
