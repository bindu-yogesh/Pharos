import csv
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEATHER_DATA_FILE = PROJECT_ROOT / "data" / "weather_observations.csv"

REQUIRED_COLUMNS = {
    "State",
    "District",
    "Date",
    "daily_rainfall_mm",
    "daily_normal_rainfall_mm",
    "daily_departure_percent",
    "daily_category",
    "source_dataset",
    "source_url",
    "record_type",
}


def load_weather_observations():
    """Load and validate district-level daily rainfall observations."""
    observations = []

    with open(WEATHER_DATA_FILE, "r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)

        if not reader.fieldnames:
            raise ValueError("Weather CSV is empty or has no header")

        missing_columns = REQUIRED_COLUMNS - set(reader.fieldnames)
        if missing_columns:
            raise ValueError(
                f"Weather CSV is missing columns: {sorted(missing_columns)}"
            )

        for row_number, row in enumerate(reader, start=2):
            try:
                observation_date = date.fromisoformat(row["Date"])
                rainfall = float(row["daily_rainfall_mm"])
                normal_rainfall = float(row["daily_normal_rainfall_mm"])
            except (ValueError, TypeError) as error:
                raise ValueError(
                    f"Invalid date or rainfall value on CSV row {row_number}"
                ) from error

            if rainfall < 0 or normal_rainfall < 0:
                raise ValueError(
                    f"Rainfall cannot be negative on CSV row {row_number}"
                )

            if not row["District"].strip():
                raise ValueError(
                    f"District is missing on CSV row {row_number}"
                )

            observations.append({
                **row,
                "Date": observation_date.isoformat(),
                "daily_rainfall_mm": rainfall,
                "daily_normal_rainfall_mm": normal_rainfall,
            })

    return observations


def get_district_rainfall(district, observation_date):
    """
    Return rainfall data for a district and date.

    Returns None when no matching observation exists.
    """
    if isinstance(observation_date, str):
        observation_date = date.fromisoformat(observation_date)

    observations = load_weather_observations()

    for observation in observations:
        if (
            observation["District"].strip().casefold()
            == district.strip().casefold()
            and date.fromisoformat(observation["Date"]) == observation_date
        ):
            return observation

    return None


def is_heavy_rain(observation):
    """Classify a valid observation using the initial IMD threshold."""
    if observation is None:
        return None

    return observation["daily_rainfall_mm"] >= 64.5
