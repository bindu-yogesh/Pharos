
import csv
from datetime import date
from pathlib import Path

from geoalchemy2 import WKTElement
from sqlalchemy.dialects.postgresql import insert

from backend.app.database import SessionLocal
from backend.app.models.incident import IncidentHistory


DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "incidents.csv"


def import_incidents() -> None:
    imported = 0
    without_coordinates = 0

    with DATA_FILE.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        with SessionLocal() as session:
            for row in reader:
                external_id = row["id"].strip()

                if not external_id:
                    raise ValueError("Incident row has no ID.")

                latitude_text = (row.get("latitude") or "").strip()
                longitude_text = (row.get("longitude") or "").strip()

                # Never invent coordinates. If either is missing,
                # preserve the incident with NULL geometry.
                geom = None
                location_confidence = "unknown"

                if latitude_text and longitude_text:
                    latitude = float(latitude_text)
                    longitude = float(longitude_text)

                    if not -90 <= latitude <= 90:
                        raise ValueError(
                            f"Invalid latitude for {external_id}: {latitude}"
                        )

                    if not -180 <= longitude <= 180:
                        raise ValueError(
                            f"Invalid longitude for {external_id}: {longitude}"
                        )

                    geom = WKTElement(
                        f"POINT({longitude} {latitude})",
                        srid=4326,
                    )
                else:
                    without_coordinates += 1

                values = {
                    "external_id": external_id,
                    "incident_date": date.fromisoformat(
                        row["date"].strip()
                    ),
                    "type": row["type"].strip(),
                    "location_name": row["location"].strip(),
                    "geom": geom,
                    "location_confidence": location_confidence,
                    "source": row["source"].strip(),
                    "notes": row.get("notes", "").strip() or None,
                }

                statement = insert(IncidentHistory).values(**values)

                statement = statement.on_conflict_do_update(
                    index_elements=[IncidentHistory.external_id],
                    set_={
                        "incident_date": statement.excluded.incident_date,
                        "type": statement.excluded.type,
                        "location_name": statement.excluded.location_name,
                        "geom": statement.excluded.geom,
                        "location_confidence": (
                            statement.excluded.location_confidence
                        ),
                        "source": statement.excluded.source,
                        "notes": statement.excluded.notes,
                    },
                )

                session.execute(statement)
                imported += 1

            session.commit()

    print(
        f"{imported} imported or updated; "
        f"{without_coordinates} without coordinates."
    )


if __name__ == "__main__":
    import_incidents()
