import pytest
import yaml

from risk_engine import scorer as scorer_module
from risk_engine.scorer import calculate_risk


def complete_flags(**overrides):
    flags = {
        "heavy_rain": False,
        "landslide_history": False,
        "steep_slope": False,
        "recent_hazard_report": False,
        "heavy_traffic": False,
        "low_visibility": False,
    }
    flags.update(overrides)
    return flags


def test_missing_inputs_return_incomplete_without_score():
    result = calculate_risk()

    assert result["risk_assessment"] == "incomplete"
    assert result["score"] is None
    assert result["level"] is None
    assert len(result["risk_data_gaps"]) == 6


def test_partial_inputs_return_incomplete_without_score():
    result = calculate_risk(heavy_rain=True)

    assert result["risk_assessment"] == "incomplete"
    assert result["score"] is None
    assert result["level"] is None
    assert "heavy_traffic" in result["risk_data_gaps"]
    assert result["reasons"] == ["Heavy rain"]


def test_no_risk_with_all_inputs_known():
    result = calculate_risk(**complete_flags())

    assert result["risk_assessment"] == "complete"
    assert result["score"] == 0
    assert result["level"] == "Green"
    assert result["reasons"] == []


def test_heavy_rain():
    result = calculate_risk(**complete_flags(heavy_rain=True))

    assert result["score"] == 30
    assert result["level"] == "Green"
    assert "Heavy rain" in result["reasons"]


def test_multiple_risk_factors():
    result = calculate_risk(**complete_flags(
        heavy_rain=True,
        steep_slope=True,
        heavy_traffic=True,
    ))

    assert result["score"] == 75
    assert result["level"] == "Orange"


def test_score_is_capped_at_100():
    result = calculate_risk(**complete_flags(
        heavy_rain=True,
        landslide_history=True,
        steep_slope=True,
        recent_hazard_report=True,
        heavy_traffic=True,
        low_visibility=True,
    ))

    assert result["score"] == 100
    assert result["level"] == "Red"


@pytest.mark.parametrize(
    "expected_score, expected_level, overrides",
    [
        (30, "Green", {"heavy_rain": True}),
        (45, "Yellow", {"heavy_rain": True, "low_visibility": True}),
        (55, "Orange", {"heavy_rain": True, "landslide_history": True}),
        (55, "Orange", {"heavy_rain": True, "heavy_traffic": True}),
        (75, "Orange", {
            "heavy_rain": True,
            "steep_slope": True,
            "heavy_traffic": True,
        }),
        (90, "Red", {
            "heavy_rain": True,
            "landslide_history": True,
            "steep_slope": True,
            "low_visibility": True,
        }),
        (100, "Red", {
            "heavy_rain": True,
            "landslide_history": True,
            "steep_slope": True,
            "recent_hazard_report": True,
            "heavy_traffic": True,
            "low_visibility": True,
        }),
    ],
)
def test_risk_levels(expected_score, expected_level, overrides):
    result = calculate_risk(**complete_flags(**overrides))

    assert result["score"] == expected_score
    assert result["level"] == expected_level
    assert result["risk_assessment"] == "complete"


@pytest.mark.parametrize("invalid", ["false", 1, 0, None])
def test_non_boolean_values_are_not_accepted_as_known_flags(invalid):
    if invalid is None:
        result = calculate_risk(**complete_flags(heavy_traffic=None))
        assert result["score"] is None
    else:
        with pytest.raises(ValueError, match="must be booleans"):
            calculate_risk(**complete_flags(heavy_traffic=invalid))


def test_risk_thresholds_are_loaded_from_yaml(tmp_path, monkeypatch):
    custom_rules = {
        "risk_rules": {
            "heavy_rain": {"points": 30},
            "landslide_history": {"points": 25},
            "steep_slope": {"points": 20},
            "recent_hazard_report": {"points": 40},
            "heavy_traffic": {"points": 25},
            "low_visibility": {"points": 15},
        },
        "risk_levels": {
            "green": {"min": 0, "max": 10},
            "yellow": {"min": 11, "max": 40},
            "orange": {"min": 41, "max": 75},
            "red": {"min": 76, "max": 100},
        },
        "max_score": 100,
    }

    rules_file = tmp_path / "rules.yaml"
    rules_file.write_text(
        yaml.safe_dump(custom_rules),
        encoding="utf-8",
    )
    monkeypatch.setattr(scorer_module, "RULES_FILE", rules_file)

    result = calculate_risk(**complete_flags(heavy_rain=True))

    assert result["score"] == 30
    assert result["level"] == "Yellow"


def _write_custom_rules(tmp_path, monkeypatch, points=30, max_score=100):
    config = {
        "risk_rules": {
            "heavy_rain": {"points": points},
            "landslide_history": {"points": 25},
            "steep_slope": {"points": 20},
            "recent_hazard_report": {"points": 40},
            "heavy_traffic": {"points": 25},
            "low_visibility": {"points": 15},
        },
        "risk_levels": {
            "green": {"min": 0, "max": 30},
            "yellow": {"min": 31, "max": 50},
            "orange": {"min": 51, "max": 75},
            "red": {"min": 76, "max": 100},
        },
        "max_score": max_score,
    }
    rules_file = tmp_path / "rules.yaml"
    rules_file.write_text(yaml.safe_dump(config), encoding="utf-8")
    monkeypatch.setattr(scorer_module, "RULES_FILE", rules_file)


@pytest.mark.parametrize("invalid", [-1, float("inf"), float("nan"), True, "30"])
def test_invalid_risk_weights_are_rejected(tmp_path, monkeypatch, invalid):
    _write_custom_rules(tmp_path, monkeypatch, points=invalid)
    with pytest.raises(ValueError, match="points value"):
        calculate_risk(**complete_flags())


@pytest.mark.parametrize("invalid", [0, -1, float("inf"), float("nan"), True, "100"])
def test_invalid_max_score_is_rejected(tmp_path, monkeypatch, invalid):
    _write_custom_rules(tmp_path, monkeypatch, max_score=invalid)
    with pytest.raises(ValueError, match="max_score"):
        calculate_risk(**complete_flags())


def test_configured_score_cap_is_applied(tmp_path, monkeypatch):
    _write_custom_rules(tmp_path, monkeypatch, max_score=80)
    result = calculate_risk(**complete_flags(
        heavy_rain=True,
        landslide_history=True,
        steep_slope=True,
        recent_hazard_report=True,
        heavy_traffic=True,
        low_visibility=True,
    ))
    assert result["score"] == 80
