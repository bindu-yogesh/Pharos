
import json
from pathlib import Path
from risk_engine.incident_data import load_incidents
from risk_engine.incident_matching import match_incidents_to_segments
from risk_engine.scorer import calculate_risk
from risk_engine.weather_data import (
    get_district_rainfall,
    is_heavy_rain,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]

ROUTE_DATA_FILE = (
    PROJECT_ROOT
    / "data"
    / "route_segments_with_slope.json"
)

STEEP_SLOPE_THRESHOLD = 6.0


# Reads the segmented route data from disk.
def load_route_segments():
    with open(ROUTE_DATA_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


# Calculates the risk score for each route segment.
# Rainfall is optional and requires both a district and a date.
def score_route_segments(district=None, observation_date=None):

    if (district is None) != (observation_date is None):
        raise ValueError(
            "district and observation_date must be provided together"
        )

    rainfall_observation = None

    if district is not None:
        rainfall_observation = get_district_rainfall(
            district,
            observation_date,
        )

    heavy_rain = is_heavy_rain(rainfall_observation)

    segments = load_route_segments()
    incidents = load_incidents()

    landslide_incidents = [
        incident for incident in incidents
        if incident["type"] == "landslide"
    ]

    landslide_location_coverage_complete = (
        bool(landslide_incidents)
        and all(
            incident["latitude"] is not None
            and incident["longitude"] is not None
            for incident in landslide_incidents
        )
    )

    incident_matches = match_incidents_to_segments(
        landslide_incidents,
        segments,
        max_distance_m=500,
    )

    results = []

    for segment in segments:
        slope = segment["slope_percent"]

        # Detects both steep climbs and steep descents.
        is_steep = abs(slope) >= STEEP_SLOPE_THRESHOLD

        incident_ids = incident_matches[segment["segment_id"]]
        has_landslide_history = (
            True if incident_ids
            else False if landslide_location_coverage_complete
            else None
        )

        risk = calculate_risk(
            steep_slope=is_steep,
            heavy_rain=heavy_rain,
            landslide_history=has_landslide_history,
            recent_hazard_report=None,
            heavy_traffic=None,
            low_visibility=None,
        )

        results.append({
            "historical_incident_ids": incident_ids,
            "segment_id": segment["segment_id"],
            "length_m": segment["length_m"],
            "slope_percent": slope,
            "risk_score": risk["score"],
            "known_risk_score": risk["known_score"],
            "risk_status": risk["status"],
            "missing_factors": risk["missing_factors"],
            "risk_level": risk["level"],
            "reasons": risk["reasons"],
            "rainfall_mm": (
                rainfall_observation["daily_rainfall_mm"]
                if rainfall_observation is not None
                else None
            ),
            "weather_observation_date": (
                rainfall_observation["Date"]
                if rainfall_observation is not None
                else None
            ),
        })

    return results


# Runs the demonstration only when this file is executed directly.
if __name__ == "__main__":
    scored_segments = score_route_segments()

    for segment in scored_segments:
        print(
            f"Segment {segment['segment_id']}: "
            f"slope={segment['slope_percent']}%, "
            f"score={segment['risk_score']}, "
            f"level={segment['risk_level']}, "
            f"reasons={segment['reasons']}, "
            f"rainfall={segment['rainfall_mm']} mm, "
            f"weather_date={segment['weather_observation_date']}"
        )
