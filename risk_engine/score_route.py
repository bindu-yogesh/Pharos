import json
from datetime import datetime, timedelta, timezone
from math import isfinite
from pathlib import Path

from risk_engine.incident_data import load_incidents
from risk_engine.incident_matching import match_incidents_to_segments
from risk_engine.live_providers import (
    fetch_recent_hazard_matches,
    fetch_traffic_for_segment,
    fetch_weather_for_segments,
)
from risk_engine.scorer import calculate_risk
from risk_engine.weather_data import get_district_rainfall, is_heavy_rain

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ROUTE_DATA_FILE = PROJECT_ROOT / "data" / "route_segments_with_slope.json"
STEEP_SLOPE_THRESHOLD = 6.0


def load_route_segments():
    with open(ROUTE_DATA_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def score_route_segments(
    district=None,
    observation_date=None,
    *,
    include_live_data=False,
    route_duration_s=None,
    reverse=False,
    now=None,
):
    """Score route segments using historical and optional live observations."""
    if (district is None) != (observation_date is None):
        raise ValueError("district and observation_date must be provided together")
    if route_duration_s is not None and (
        not isinstance(route_duration_s, (int, float))
        or isinstance(route_duration_s, bool)
        or not isfinite(route_duration_s)
        or route_duration_s < 0
    ):
        raise ValueError("route_duration_s must be a non-negative number")

    rainfall_observation = (
        get_district_rainfall(district, observation_date)
        if district is not None else None
    )
    historical_heavy_rain = is_heavy_rain(rainfall_observation)
    segments = load_route_segments()
    incidents = load_incidents()
    landslides = [item for item in incidents if item["type"] == "landslide"]

    geocoded_coverage_complete = bool(landslides) and all(
        item["latitude"] is not None and item["longitude"] is not None
        for item in landslides
    )
    incident_matches = match_incidents_to_segments(
        landslides, segments, max_distance_m=500
    )

    base_time = now or datetime.now(timezone.utc)
    if base_time.tzinfo is None:
        base_time = base_time.replace(tzinfo=timezone.utc)
    travel_segments = list(reversed(segments)) if reverse else segments
    total_length = sum(float(item["length_m"]) for item in travel_segments) or 1.0
    elapsed_distance = 0.0
    arrival_times = []
    for segment in travel_segments:
        offset = (
            elapsed_distance / total_length * route_duration_s
            if route_duration_s is not None else 0
        )
        arrival_times.append(base_time + timedelta(seconds=offset))
        elapsed_distance += float(segment["length_m"])

    weather_by_id = {}
    traffic_by_id = {}
    recent_by_id = None
    if include_live_data:
        weather_values = fetch_weather_for_segments(travel_segments, arrival_times)
        weather_by_id = {
            item["segment_id"]: value
            for item, value in zip(travel_segments, weather_values)
        }
        for segment in segments:
            start, end = segment["start"], segment["end"]
            latitude = (start[1] + end[1]) / 2
            longitude = (start[0] + end[0]) / 2
            traffic_by_id[segment["segment_id"]] = fetch_traffic_for_segment(
                latitude, longitude
            )
        recent_by_id = fetch_recent_hazard_matches(segments)

    results = []
    for segment in segments:
        segment_id = segment["segment_id"]
        slope = float(segment["slope_percent"])
        incident_ids = incident_matches[segment_id]
        historical_landslide = (
            True if incident_ids
            else False if geocoded_coverage_complete
            else None
        )

        weather = weather_by_id.get(segment_id)
        heavy_rain = (
            weather["heavy_rain"] if weather is not None
            else historical_heavy_rain
        )
        low_visibility = (
            weather["low_visibility"] if weather is not None else None
        )
        traffic = traffic_by_id.get(segment_id)
        heavy_traffic = (
            traffic["heavy_traffic"] if traffic is not None else None
        )
        recent_ids = (
            recent_by_id.get(segment_id, []) if recent_by_id is not None else None
        )
        recent_hazard = bool(recent_ids) if recent_ids is not None else None

        risk = calculate_risk(
            steep_slope=abs(slope) >= STEEP_SLOPE_THRESHOLD,
            heavy_rain=heavy_rain,
            landslide_history=historical_landslide,
            recent_hazard_report=recent_hazard,
            heavy_traffic=heavy_traffic,
            low_visibility=low_visibility,
        )

        results.append({
            "segment_id": segment_id,
            "length_m": segment["length_m"],
            "slope_percent": slope,
            "risk_score": risk["score"],
            "known_risk_score": risk["known_score"],
            "risk_status": risk["status"],
            "missing_factors": risk["missing_factors"],
            "risk_level": risk["level"],
            "reasons": risk["reasons"],
            "historical_incident_ids": incident_ids,
            "recent_hazard_report_ids": recent_ids,
            "rainfall_mm": (
                weather["precipitation_mm"] if weather is not None
                else rainfall_observation["daily_rainfall_mm"]
                if rainfall_observation is not None else None
            ),
            "visibility_m": weather["visibility_m"] if weather else None,
            "weather_observation_date": (
                weather["forecast_time"] if weather is not None
                else rainfall_observation["Date"]
                if rainfall_observation is not None else None
            ),
            "traffic": traffic,
            "data_sources": {
                "weather": weather["source"] if weather else (
                    "historical_weather_dataset" if rainfall_observation else None
                ),
                "traffic": traffic["source"] if traffic else None,
                "community_reports": "postgis" if recent_by_id is not None else None,
            },
        })
    return results


if __name__ == "__main__":
    for item in score_route_segments():
        print(
            f"Segment {item['segment_id']}: "
            f"score={item['risk_score']}, "
            f"known={item['known_risk_score']}, "
            f"status={item['risk_status']}, "
            f"missing={item['missing_factors']}"
        )
