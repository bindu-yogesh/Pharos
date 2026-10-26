
import csv
from datetime import date
from math import isfinite
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INCIDENT_DATA_FILE = PROJECT_ROOT / "data" / "incidents.csv"

REQUIRED_COLUMNS = {
    "id",
    "date",
    "type",
    "location",
    "latitude",
    "longitude",
    "source",
    "notes",
}


def load_incidents():
    """Load and validate historical incident records."""
    incidents = []
    seen_ids = set()

    with open(
        INCIDENT_DATA_FILE, "r", encoding="utf-8-sig", newline=""
    ) as file:
        reader = csv.DictReader(file)

        if not reader.fieldnames:
            raise ValueError("Incident CSV is empty or has no header")

        missing_columns = REQUIRED_COLUMNS - set(reader.fieldnames)
        if missing_columns:
            raise ValueError(
                f"Incident CSV is missing columns: {sorted(missing_columns)}"
            )

        for row_number, row in enumerate(reader, start=2):
            incident_id = row["id"].strip()

            if not incident_id:
                raise ValueError(
                    f"Incident ID is missing on CSV row {row_number}"
                )

            if incident_id in seen_ids:
                raise ValueError(
                    f"Duplicate incident ID '{incident_id}' "
                    f"on CSV row {row_number}"
                )

            seen_ids.add(incident_id)

            try:
                incident_date = date.fromisoformat(row["date"].strip())
            except (ValueError, TypeError, AttributeError) as error:
                raise ValueError(
                    f"Invalid incident date on CSV row {row_number}"
                ) from error

            for field in ("type", "location", "source", "notes"):
                if not row[field] or not row[field].strip():
                    raise ValueError(
                        f"Missing '{field}' on CSV row {row_number}"
                    )

            latitude_text = row["latitude"].strip()
            longitude_text = row["longitude"].strip()

            # Coordinates must either both exist or both be absent.
            if bool(latitude_text) != bool(longitude_text):
                raise ValueError(
                    f"Incomplete coordinates on CSV row {row_number}"
                )

            latitude = None
            longitude = None

            if latitude_text and longitude_text:
                try:
                    latitude = float(latitude_text)
                    longitude = float(longitude_text)
                except ValueError as error:
                    raise ValueError(
                        f"Invalid coordinates on CSV row {row_number}"
                    ) from error

                if (
                    not isfinite(latitude)
                    or not isfinite(longitude)
                    or not -90 <= latitude <= 90
                    or not -180 <= longitude <= 180
                ):
                    raise ValueError(
                        f"Coordinates out of range on CSV row {row_number}"
                    )

            incidents.append({
                "id": incident_id,
                "date": incident_date.isoformat(),
                "type": row["type"].strip().casefold(),
                "location": row["location"].strip(),
                "latitude": latitude,
                "longitude": longitude,
                "source": row["source"].strip(),
                "notes": row["notes"].strip(),
            })

    return incidents
