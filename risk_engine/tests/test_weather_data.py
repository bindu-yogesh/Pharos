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
from pathlib import Path
import csv

import pytest
import risk_engine.weather_data as weather_data


def write_weather_csv(path, rows):
    fields = [
        "State", "District", "Date",
        "daily_rainfall_mm", "daily_normal_rainfall_mm",
        "daily_departure_percent", "daily_category",
        "source_dataset", "source_url", "record_type",
    ]

    with open(path, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def valid_weather_row():
    return {
        "State": "KARNATAKA",
        "District": "HASSAN",
        "Date": "2026-09-15",
        "daily_rainfall_mm": "10.0",
        "daily_normal_rainfall_mm": "20.0",
        "daily_departure_percent": "-50%",
        "daily_category": "LD",
        "source_dataset": "test_dataset",
        "source_url": "https://example.com/weather",
        "record_type": "district_daily_rainfall_observation",
    }


@pytest.mark.parametrize("field,value", [
    ("daily_rainfall_mm", "nan"),
    ("daily_rainfall_mm", "inf"),
    ("daily_normal_rainfall_mm", "-inf"),
])
def test_rejects_non_finite_rainfall(tmp_path, monkeypatch, field, value):
    row = valid_weather_row()
    row[field] = value

    path = tmp_path / "weather.csv"
    write_weather_csv(path, [row])
    monkeypatch.setattr(weather_data, "WEATHER_DATA_FILE", path)

    with pytest.raises(ValueError):
        weather_data.load_weather_observations()


def test_rejects_duplicate_district_date(tmp_path, monkeypatch):
    row = valid_weather_row()
    duplicate = {**row, "daily_rainfall_mm": "15.0"}

    path = tmp_path / "weather.csv"
    write_weather_csv(path, [row, duplicate])
    monkeypatch.setattr(weather_data, "WEATHER_DATA_FILE", path)

    with pytest.raises(ValueError, match="Duplicate"):
        weather_data.load_weather_observations()


def test_rejects_invalid_departure_percentage(tmp_path, monkeypatch):
    row = valid_weather_row()
    row["daily_departure_percent"] = "unknown"

    path = tmp_path / "weather.csv"
    write_weather_csv(path, [row])
    monkeypatch.setattr(weather_data, "WEATHER_DATA_FILE", path)

    with pytest.raises(ValueError):
        weather_data.load_weather_observations()


def test_rejects_missing_source_metadata(tmp_path, monkeypatch):
    row = valid_weather_row()
    row["source_dataset"] = ""

    path = tmp_path / "weather.csv"
    write_weather_csv(path, [row])
    monkeypatch.setattr(weather_data, "WEATHER_DATA_FILE", path)

    with pytest.raises(ValueError, match="source_dataset"):
        weather_data.load_weather_observations()
