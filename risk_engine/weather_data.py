import csv
from datetime import date
from math import isfinite
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEATHER_DATA_FILE = PROJECT_ROOT / "data" / "weather_observations.csv"

HEAVY_RAIN_THRESHOLD_MM = 64.5

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
    seen_observations = set()

    with open(
        WEATHER_DATA_FILE, "r", encoding="utf-8-sig", newline=""
    ) as file:
        reader = csv.DictReader(file)

        if not reader.fieldnames:
            raise ValueError("Weather CSV is empty or has no header")

        if len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError("Weather CSV contains duplicate column names")

        missing_columns = REQUIRED_COLUMNS - set(reader.fieldnames)
        if missing_columns:
            raise ValueError(
                f"Weather CSV is missing columns: {sorted(missing_columns)}"
            )

        for row_number, row in enumerate(reader, start=2):
            try:
                observation_date = date.fromisoformat(row["Date"].strip())
                rainfall = float(row["daily_rainfall_mm"])
                normal_rainfall = float(row["daily_normal_rainfall_mm"])
                departure_text = row["daily_departure_percent"].strip()
                departure = float(departure_text.removesuffix("%"))
            except (ValueError, TypeError, AttributeError) as error:
                raise ValueError(
                    f"Invalid date or rainfall metadata on CSV row {row_number}"
                ) from error

            if not all(isfinite(value) for value in (
                rainfall, normal_rainfall, departure
            )):
                raise ValueError(
                    f"Non-finite weather value on CSV row {row_number}"
                )

            if rainfall < 0 or normal_rainfall < 0:
                raise ValueError(
                    f"Rainfall cannot be negative on CSV row {row_number}"
                )

            for field in (
                "State",
                "District",
                "daily_category",
                "source_dataset",
                "source_url",
                "record_type",
            ):
                if not row[field] or not row[field].strip():
                    raise ValueError(
                        f"Missing '{field}' on CSV row {row_number}"
                    )

            if row["record_type"].strip() != (
                "district_daily_rainfall_observation"
            ):
                raise ValueError(
                    f"Unsupported record type on CSV row {row_number}"
                )

            observation_key = (
                row["State"].strip().casefold(),
                row["District"].strip().casefold(),
                observation_date,
            )

            if observation_key in seen_observations:
                raise ValueError(
                    f"Duplicate district/date observation on CSV row {row_number}"
                )

            seen_observations.add(observation_key)

            observations.append({
                **row,
                "State": row["State"].strip(),
                "District": row["District"].strip(),
                "Date": observation_date.isoformat(),
                "daily_rainfall_mm": rainfall,
                "daily_normal_rainfall_mm": normal_rainfall,
            })

    return observations


def get_district_rainfall(district, observation_date):
    """Return rainfall for a district and date, or None if unavailable."""
    if not isinstance(district, str) or not district.strip():
        raise ValueError("district must be a non-empty string")

    if isinstance(observation_date, str):
        try:
            observation_date = date.fromisoformat(observation_date)
        except ValueError as error:
            raise ValueError("observation_date must be a valid ISO date") from error

    if not isinstance(observation_date, date):
        raise ValueError("observation_date must be a date or ISO date string")

    observations = load_weather_observations()

    for observation in observations:
        if (
            observation["District"].casefold() == district.strip().casefold()
            and date.fromisoformat(observation["Date"]) == observation_date
        ):
            return observation

    return None


def is_heavy_rain(observation):
    """Classify daily rainfall using the configured initial threshold."""
    if observation is None:
        return None

    try:
        rainfall = observation["daily_rainfall_mm"]
    except (KeyError, TypeError) as error:
        raise ValueError("Weather observation is missing rainfall") from error

    if (
        not isinstance(rainfall, (int, float))
        or isinstance(rainfall, bool)
        or not isfinite(rainfall)
        or rainfall < 0
    ):
        raise ValueError("Rainfall must be a finite non-negative number")

    return rainfall >= HEAVY_RAIN_THRESHOLD_MM
