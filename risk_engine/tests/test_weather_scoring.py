
import pytest

from risk_engine.score_route import score_route_segments


def test_route_scoring_without_weather():
    results = score_route_segments()

    assert len(results) == 28
    assert all(result["rainfall_mm"] is None for result in results)
    assert all(
        result["weather_observation_date"] is None
        for result in results
    )


def test_route_scoring_with_historical_rainfall():
    results = score_route_segments(
        district="DAKSHIN KANNADA",
        observation_date="2026-09-25",
    )

    assert len(results) == 28
    assert all(result["rainfall_mm"] == 48.5 for result in results)
    assert all(
        result["weather_observation_date"] == "2026-09-25"
        for result in results
    )


def test_district_and_date_must_be_provided_together():
    with pytest.raises(ValueError):
        score_route_segments(district="DAKSHIN KANNADA")

    with pytest.raises(ValueError):
        score_route_segments(observation_date="2026-09-25")


def test_missing_weather_observation_is_not_zero_rainfall():
    results = score_route_segments(
        district="UNKNOWN DISTRICT",
        observation_date="2026-09-25",
    )

    assert all(result["rainfall_mm"] is None for result in results)
