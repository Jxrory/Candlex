import pytest
from src.tools.indicators import IndicatorSpec


def test_parse_shorthand_no_params():
    from src.services.indicators_service import parse_specs
    result = parse_specs(["macd"])
    assert result == [IndicatorSpec("macd")]


def test_parse_shorthand_with_params():
    from src.services.indicators_service import parse_specs
    result = parse_specs(["ma:5"])
    assert result == [IndicatorSpec("ma", {"n": 5})]


def test_parse_shorthand_multi_params():
    from src.services.indicators_service import parse_specs
    result = parse_specs(["boll:20,2.0"])
    assert result == [IndicatorSpec("boll", {"n": 20, "k": 2.0})]


def test_parse_json_format():
    from src.services.indicators_service import parse_specs
    result = parse_specs(['[{"name":"ma","params":{"n":5}}]'])
    assert result == [IndicatorSpec("ma", {"n": 5})]


def test_parse_mixed():
    from src.services.indicators_service import parse_specs
    result = parse_specs(["ma:5", '[{"name":"macd","params":{"fast":12,"slow":26,"signal":9}}]'])
    assert result == [
        IndicatorSpec("ma", {"n": 5}),
        IndicatorSpec("macd", {"fast": 12, "slow": 26, "signal": 9}),
    ]


def test_parse_empty():
    from src.services.indicators_service import parse_specs
    result = parse_specs([])
    assert result == []


def test_parse_unknown_indicator():
    from src.services.indicators_service import parse_specs
    with pytest.raises(ValueError, match="unsupported indicator"):
        parse_specs(["unknown:5"])


def test_parse_unknown_indicator_json():
    from src.services.indicators_service import parse_specs
    with pytest.raises(ValueError, match="unsupported indicator"):
        parse_specs(['[{"name":"INVALID","params":{}}]'])


def test_parse_dedup_identical_shorthand():
    from src.services.indicators_service import parse_specs
    result = parse_specs(["ma:5", "ma:5"])
    assert len(result) == 1
    assert result == [IndicatorSpec("ma", {"n": 5})]


def test_parse_dedup_shorthand_and_json():
    from src.services.indicators_service import parse_specs
    result = parse_specs(["ma:5", '[{"name":"ma","params":{"n":5}}]'])
    assert len(result) == 1
    assert result == [IndicatorSpec("ma", {"n": 5})]


def test_parse_json_multi_entry():
    from src.services.indicators_service import parse_specs
    result = parse_specs(['[{"name":"ma","params":{"n":5}},{"name":"rsi","params":{"n":14}}]'])
    assert result == [
        IndicatorSpec("ma", {"n": 5}),
        IndicatorSpec("rsi", {"n": 14}),
    ]
