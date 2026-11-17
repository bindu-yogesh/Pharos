import pytest

from risk_engine.scorer import calculate_risk


def test_no_risk():
    result = calculate_risk()

    assert result["score"] == 0
    assert result["level"] == "Green"
    assert result["reasons"] == []


def test_heavy_rain():
    result = calculate_risk(heavy_rain=True)

    assert result["score"] == 30
    assert result["level"] == "Green"
    assert "Heavy rain" in result["reasons"]


def test_multiple_risk_factors():
    result = calculate_risk(
        heavy_rain=True,
        steep_slope=True,
        heavy_traffic=True,
    )

    assert result["score"] == 75
    assert result["level"] == "Orange"


def test_score_is_capped_at_100():
    result = calculate_risk(
        heavy_rain=True,
        landslide_history=True,
        steep_slope=True,
        recent_hazard_report=True,
        heavy_traffic=True,
        low_visibility=True,
    )

    assert result["score"] == 100
    assert result["level"] == "Red"


@pytest.mark.parametrize(
    "expected_score, expected_level, kwargs",
    [
        (30, "Green", {"heavy_rain": True}),
        (45, "Yellow", {"heavy_rain": True, "low_visibility": True}),
        (55, "Orange", {"heavy_rain": True, "landslide_history": True}),
        (55, "Orange", {"heavy_rain": True, "heavy_traffic": True}),
        (
            75,
            "Orange",
            {
                "heavy_rain": True,
                "steep_slope": True,
                "heavy_traffic": True,
            },
        ),
        (
            90,
            "Red",
            {
                "heavy_rain": True,
                "landslide_history": True,
                "steep_slope": True,
                "low_visibility": True,
            },
        ),
        (
            100,
            "Red",
            {
                "heavy_rain": True,
                "landslide_history": True,
                "steep_slope": True,
                "recent_hazard_report": True,
                "heavy_traffic": True,
                "low_visibility": True,
            },
        ),
    ],
)
def test_risk_levels(expected_score, expected_level, kwargs):
    result = calculate_risk(**kwargs)

    assert result["score"] == expected_score
    assert result["level"] == expected_level
def test_unknown_factor_makes_assessment_incomplete():
    result = calculate_risk(heavy_rain=True, heavy_traffic=None)

    assert result["score"] is None
    assert result["known_score"] == 30
    assert result["level"] is None
    assert result["status"] == "incomplete"
    assert result["missing_factors"] == ["heavy_traffic"]
    assert "Heavy rain" in result["reasons"]


def test_all_known_false_factors_produce_zero_risk():
    result = calculate_risk(
        heavy_rain=False,
        landslide_history=False,
        steep_slope=False,
        recent_hazard_report=False,
        heavy_traffic=False,
        low_visibility=False,
    )

    assert result["score"] == 0
    assert result["level"] == "Green"
    assert result["status"] == "complete"


def test_invalid_factor_value_is_rejected():
    with pytest.raises(TypeError):
        calculate_risk(heavy_rain="unknown")
