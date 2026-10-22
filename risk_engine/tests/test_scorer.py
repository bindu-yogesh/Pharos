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