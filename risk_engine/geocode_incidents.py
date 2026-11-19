"""Create reviewable Nominatim candidates; never auto-approve village centroids."""
import csv
import time
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "incidents.csv"
OUTPUT = ROOT / "data" / "incident_geocode_candidates.csv"
URL = "https://nominatim.openstreetmap.org/search"


def main():
    with SOURCE.open(encoding="utf-8-sig", newline="") as handle:
        incidents = list(csv.DictReader(handle))

    fields = [
        "incident_id", "location_query", "latitude", "longitude",
        "display_name", "osm_type", "osm_id", "precision", "verified",
        "review_notes",
    ]
    results = []
    with requests.Session() as session:
        session.headers["User-Agent"] = "PharosRoadSafetyPrototype/1.0"
        for incident in incidents:
            query = f"{incident['location']}, Shiradi Ghat, Karnataka, India"
            try:
                response = session.get(
                    URL,
                    params={
                        "q": query, "format": "jsonv2", "limit": 1,
                        "countrycodes": "in",
                        "viewbox": "75.45,13.05,75.85,12.75",
                        "bounded": 1,
                    },
                    timeout=15,
                )
                response.raise_for_status()
                matches = response.json()
                match = matches[0] if matches else {}
                results.append({
                    "incident_id": incident["id"],
                    "location_query": query,
                    "latitude": match.get("lat", ""),
                    "longitude": match.get("lon", ""),
                    "display_name": match.get("display_name", ""),
                    "osm_type": match.get("osm_type", ""),
                    "osm_id": match.get("osm_id", ""),
                    "precision": "locality_candidate" if match else "unresolved",
                    "verified": "false",
                    "review_notes": (
                        "Candidate only. Verify against the original incident "
                        "source; do not treat a locality centre as the accident point."
                    ),
                })
            except requests.RequestException as error:
                results.append({
                    "incident_id": incident["id"],
                    "location_query": query,
                    "latitude": "", "longitude": "", "display_name": "",
                    "osm_type": "", "osm_id": "", "precision": "geocoding_error",
                    "verified": "false", "review_notes": str(error),
                })
            time.sleep(1.1)

    with OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(results)
    print(f"Wrote {len(results)} review candidates to {OUTPUT}")


if __name__ == "__main__":
    main()
