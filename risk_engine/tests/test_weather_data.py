from datetime import date
from risk_engine.weather_data import load_weather_observations


def test_weather_dataset_loads_100_records():
    observations = load_weather_observations()

    assert len(observations) == 100


def test_weather_observations_have_valid_values():
    observations = load_weather_observations()

    for observation in observations:
        assert observation["State"] == "KARNATAKA"
        assert observation["District"]
        assert observation["daily_rainfall_mm"] >= 0
        assert observation["daily_normal_rainfall_mm"] >= 0


def test_weather_observations_include_source_metadata():
    observations = load_weather_observations()

    for observation in observations:
        assert observation["source_dataset"]
        assert observation["source_url"]
        assert observation["record_type"] == "district_daily_rainfall_observation"


from risk_engine.weather_data import (
    get_district_rainfall,
    is_heavy_rain,
)


def test_lookup_finds_existing_observation():
    observation = get_district_rainfall(
        "DAKSHIN KANNADA", date(2026, 9, 15)
    )

    assert observation is not None
    assert observation["daily_rainfall_mm"] == 0.0


def test_lookup_returns_none_for_missing_observation():
    observation = get_district_rainfall(
        "UNKNOWN DISTRICT", date(2026, 9, 15)
    )

    assert observation is None


def test_heavy_rain_threshold():
    assert is_heavy_rain({"daily_rainfall_mm": 64.5}) is True
    assert is_heavy_rain({"daily_rainfall_mm": 20.0}) is False
    assert is_heavy_rain(None) is None
