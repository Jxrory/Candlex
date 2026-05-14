from datetime import date
import pytest

from app.calendar import CalendarService


@pytest.fixture
def cal():
    svc = CalendarService()
    svc._dates = [
        date(2026, 1, 5), date(2026, 1, 6), date(2026, 1, 7),
        date(2026, 1, 8), date(2026, 1, 9),
        date(2026, 1, 12), date(2026, 1, 13),
    ]
    return svc


def test_nearest_forward_exact(cal):
    assert cal.nearest_forward(date(2026, 1, 5)) == date(2026, 1, 5)


def test_nearest_forward_weekend(cal):
    assert cal.nearest_forward(date(2026, 1, 10)) == date(2026, 1, 12)


def test_nearest_forward_before_all(cal):
    assert cal.nearest_forward(date(2026, 1, 1)) == date(2026, 1, 5)


def test_nearest_backward_exact(cal):
    assert cal.nearest_backward(date(2026, 1, 5)) == date(2026, 1, 5)


def test_nearest_backward_weekend(cal):
    assert cal.nearest_backward(date(2026, 1, 10)) == date(2026, 1, 9)


def test_nearest_backward_after_all(cal):
    assert cal.nearest_backward(date(2026, 1, 31)) == date(2026, 1, 13)


def test_get_range(cal):
    result = cal.get_range(date(2026, 1, 5), date(2026, 1, 12))
    assert result == [
        date(2026, 1, 5), date(2026, 1, 6), date(2026, 1, 7),
        date(2026, 1, 8), date(2026, 1, 9), date(2026, 1, 12),
    ]
