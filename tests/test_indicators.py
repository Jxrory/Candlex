from datetime import date
import pytest
from app.tools.indicators import IndicatorSpec


def test_parse_shorthand_no_params():
    from app.indicators_service import parse_specs
    result = parse_specs(["macd"])
    assert result == [IndicatorSpec("macd")]


def test_parse_shorthand_with_params():
    from app.indicators_service import parse_specs
    result = parse_specs(["ma:5"])
    assert result == [IndicatorSpec("ma", {"n": 5})]


def test_parse_shorthand_multi_params():
    from app.indicators_service import parse_specs
    result = parse_specs(["boll:20,2.0"])
    assert result == [IndicatorSpec("boll", {"n": 20, "k": 2.0})]


def test_parse_json_format():
    from app.indicators_service import parse_specs
    result = parse_specs(['[{"name":"ma","params":{"n":5}}]'])
    assert result == [IndicatorSpec("ma", {"n": 5})]


def test_parse_mixed():
    from app.indicators_service import parse_specs
    result = parse_specs(["ma:5", '[{"name":"macd","params":{"fast":12,"slow":26,"signal":9}}]'])
    assert result == [
        IndicatorSpec("ma", {"n": 5}),
        IndicatorSpec("macd", {"fast": 12, "slow": 26, "signal": 9}),
    ]


def test_parse_empty():
    from app.indicators_service import parse_specs
    result = parse_specs([])
    assert result == []


def test_parse_unknown_indicator():
    from app.indicators_service import parse_specs
    with pytest.raises(ValueError, match="unsupported indicator"):
        parse_specs(["unknown:5"])


def test_parse_unknown_indicator_json():
    from app.indicators_service import parse_specs
    with pytest.raises(ValueError, match="unsupported indicator"):
        parse_specs(['[{"name":"INVALID","params":{}}]'])
