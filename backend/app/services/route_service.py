
"""Route processing and risk assessment built on the existing OSRM integration."""

import math
from typing import Any

from geoalchemy2 import Geography
from sqlalchemy import cast, func, select
from sqlalchemy.orm import Session

from ..models.segment import RoadSegment
from .risk_service import assess_segment_risk


SEGMENT_MATCH_RADIUS_M = 100.0

HEAVY_RAIN_THRESHOLD_MM_PER_HOUR = 15.0
LOW_VISIBILITY_THRESHOLD_M = 1000.0
SLOPE_THRESHOLD_PERCENT = 6.0

RISK_COLORS = {
    "Green": "green",
    "Yellow": "yellow",
    "Orange": "orange",
    "Red": "red",
}


def get_risk_level(score: float) -> str:
    """Map a risk score to the existing scorer's risk levels."""
    if score <= 30:
        return "Green"
    if score <= 50:
        return "Yellow"
    if score <= 75:
        return "Orange"
    return "Red"


def classify_weather_risk(
    weather: dict[str, Any] | None,
) -> tuple[bool | None, bool | None]:
    """Classify raw weather forecast values into risk flags.

    Returns:
        (heavy_rain, low_visibility)

    Missing or invalid values remain unknown rather than being treated
    as safe.
    """
    if weather is None:
        return None, None

    precipitation = weather.get("precipitation_mm")
    visibility = weather.get("visibility_m")

    try:
        if precipitation is None:
            heavy_rain = None
        else:
            precipitation_value = float(precipitation)
            if not math.isfinite(precipitation_value) or precipitation_value < 0:
                heavy_rain = None
            else:
                heavy_rain = (
                    precipitation_value
                    > HEAVY_RAIN_THRESHOLD_MM_PER_HOUR
                )

        if visibility is None:
            low_visibility = None
        else:
            visibility_value = float(visibility)
            if not math.isfinite(visibility_value) or visibility_value < 0:
                low_visibility = None
            else:
                low_visibility = (
                    visibility_value < LOW_VISIBILITY_THRESHOLD_M
                )

    except (TypeError, ValueError, OverflowError):
        return None, None

    return heavy_rain, low_visibility


def create_segments(
    coordinates: list[list[float]],
    edge_distances: list[float],
    target_length_m: float = 1000,
) -> list[dict[str, Any]]:
    """Group consecutive OSRM edges into approximately 1 km segments."""
    if target_length_m <= 0:
        raise ValueError("target_length_m must be greater than zero")

    if len(coordinates) < 2:
        raise ValueError("At least two route coordinates are required")

    if len(edge_distances) != len(coordinates) - 1:
        raise ValueError(
            "Edge-distance count must equal coordinate count minus one"
        )

    if any(distance < 0 for distance in edge_distances):
        raise ValueError("Edge distances cannot be negative")

    segments: list[dict[str, Any]] = []
    segment_coordinates = [coordinates[0]]
    segment_distance = 0.0
    segment_id = 1

    for index, distance in enumerate(edge_distances):
        edge_end = coordinates[index + 1]

        segment_distance += distance
        segment_coordinates.append(edge_end)

        if segment_distance >= target_length_m:
            segment_geometry = segment_coordinates.copy()

            segments.append({
                "segment_id": segment_id,
                "start": segment_geometry[0],
                "end": segment_geometry[-1],
                "coordinates": segment_geometry,
                "geometry": {
                    "type": "LineString",
                    "coordinates": segment_geometry,
                },
                "length_m": round(segment_distance, 2),
                "risk_status": "not_assessed",
            })

            segment_id += 1
            segment_coordinates = [edge_end]
            segment_distance = 0.0

    if segment_distance > 0:
        segment_geometry = segment_coordinates.copy()

        segments.append({
            "segment_id": segment_id,
            "start": segment_geometry[0],
            "end": segment_geometry[-1],
            "coordinates": segment_geometry,
            "geometry": {
                "type": "LineString",
                "coordinates": segment_geometry,
            },
            "length_m": round(segment_distance, 2),
            "risk_status": "not_assessed",
        })

    return segments


def process_osrm_route(route: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize one OSRM route without inventing risk scores."""
    try:
        coordinates = route["geometry"]["coordinates"]
        legs = route["legs"]
        distance_m = float(route["distance"])
        duration_s = float(route["duration"])
        annotations = [
            leg["annotation"]["distance"] for leg in legs
        ]
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(
            "OSRM route is missing geometry, distance, duration, or annotations"
        ) from exc

    if len(legs) != 1:
        raise ValueError(
            "Expected one OSRM leg for the requested origin and destination"
        )

    if not isinstance(coordinates, list) or not annotations:
        raise ValueError(
            "OSRM geometry and distance annotations must be lists"
        )

    if not isinstance(annotations[0], list):
        raise ValueError(
            "OSRM distance annotations must be a list"
        )

    segments = create_segments(coordinates, annotations[0])

    return {
        "distance_m": distance_m,
        "duration_s": duration_s,
        "geometry": route["geometry"],
        "segments": segments,
        "risk_assessment": "unavailable",
        "risk_data_gaps": [
            "Segment risk assessment has not yet been run"
        ],
    }

def assess_route_segments(
    db: Session,
    segments: list[dict[str, Any]],
    weather_by_segment: dict[int, dict[str, Any] | None] | None = None,
) -> list[dict[str, Any]]:
    """Match route segments to stored roads and assess available risk data."""
    weather_by_segment = weather_by_segment or {}
    assessed: list[dict[str, Any]] = []

    for segment in segments:
        start = segment["start"]
        end = segment["end"]
        weather = weather_by_segment.get(segment["segment_id"])

        segment_coordinates = segment.get(
            "coordinates",
            [start, end],
        )

        if len(segment_coordinates) < 2:
            raise ValueError(
                "A route segment must contain at least two coordinates"
            )

        # Build the full route segment geometry for spatial matching.
        coordinate_text = ", ".join(
            f"{float(lon)} {float(lat)}"
            for lon, lat in segment_coordinates
        )

        route_line = func.ST_GeomFromText(
            f"LINESTRING({coordinate_text})",
            4326,
        )

        route_geography = cast(
            route_line,
            Geography(srid=4326),
        )

        road_geography = cast(
            RoadSegment.geom,
            Geography(srid=4326),
        )

        distance = func.ST_Distance(
            road_geography,
            route_geography,
        )

        match = db.execute(
            select(
                RoadSegment,
                distance.label("distance_m"),
            )
            .where(
                func.ST_DWithin(
                    road_geography,
                    route_geography,
                    SEGMENT_MATCH_RADIUS_M,
                )
            )
            .order_by(distance)
            .limit(1)
        ).first()

        heavy_rain, low_visibility = classify_weather_risk(weather)

        # No stored road match means slope and database-backed risk
        # assessment cannot be completed for this segment.
        if match is None:
            gaps = [
                "No stored road segment matched within the configured radius",
                "Slope data unavailable for this segment",
                "Traffic data unavailable",
            ]

            if heavy_rain is None:
                gaps.append("Heavy-rain classification unavailable")

            if low_visibility is None:
                gaps.append("Low-visibility classification unavailable")

            assessed.append({
                **segment,
                "risk_status": "incomplete",
                "road_segment_id": None,
                "road_match_distance_m": None,
                "slope_percent": None,
                "risk_assessment": "incomplete",
                "weather_forecast": weather,
                "score": None,
                "level": None,
                "color": None,
                "reasons": [],
                "risk_flags": None,
                "risk_data_gaps": sorted(set(gaps)),
            })
            continue

        road, distance_m = match

        # Assess database-backed and weather-backed risk flags.
        risk = assess_segment_risk(
            db,
            start,
            end,
            coordinates=segment_coordinates,
            slope_percent=road.slope_percent,
            slope_threshold_percent=SLOPE_THRESHOLD_PERCENT,
            heavy_rain=heavy_rain,
            heavy_traffic=None,
            low_visibility=low_visibility,
        )

        risk_data_gaps = list(risk["risk_data_gaps"])

        if heavy_rain is None:
            risk_data_gaps.append(
                "Heavy-rain classification unavailable"
            )

        if low_visibility is None:
            risk_data_gaps.append(
                "Low-visibility classification unavailable"
            )

        if road.slope_percent is None:
            risk_data_gaps.append(
                "Slope data unavailable for this segment"
            )

        risk_data_gaps.append(
            "Traffic data unavailable"
        )

        level = risk["level"]

        assessed.append({
            **segment,
            "risk_status": risk["risk_assessment"],
            "road_segment_id": road.id,
            "road_match_distance_m": round(float(distance_m), 2),
            "slope_percent": road.slope_percent,
            "weather_forecast": weather,
            "risk_assessment": risk["risk_assessment"],
            "risk_flags": risk["risk_flags"],
            "risk_data_gaps": sorted(set(risk_data_gaps)),
            "score": risk["score"],
            "level": level,
            "color": RISK_COLORS.get(level),
            "reasons": risk["reasons"],
        })

    return assessed


def calculate_overall_route_risk(
    segments: list[dict[str, Any]],
) -> dict[str, Any]:
    """Calculate distance-weighted risk only when every segment is complete."""
    if not segments:
        return {
            "risk_assessment": "incomplete",
            "overall_risk_score": None,
            "overall_risk_level": None,
            "overall_risk_color": None,
            "overall_risk_reasons": [],
        }

    if any(
        segment.get("risk_assessment") != "complete"
        or segment.get("score") is None
        for segment in segments
    ):
        return {
            "risk_assessment": "incomplete",
            "overall_risk_score": None,
            "overall_risk_level": None,
            "overall_risk_color": None,
            "overall_risk_reasons": [],
        }

    total_distance = sum(
        float(segment["length_m"])
        for segment in segments
    )

    if total_distance <= 0:
        return {
            "risk_assessment": "incomplete",
            "overall_risk_score": None,
            "overall_risk_level": None,
            "overall_risk_color": None,
            "overall_risk_reasons": [],
        }

    weighted_score = sum(
        float(segment["score"]) * float(segment["length_m"])
        for segment in segments
    ) / total_distance

    overall_level = get_risk_level(weighted_score)

    reasons = sorted({
        reason
        for segment in segments
        for reason in segment.get("reasons", [])
    })

    return {
        "risk_assessment": "complete",
        "overall_risk_score": round(weighted_score, 2),
        "overall_risk_level": overall_level,
        "overall_risk_color": RISK_COLORS[overall_level],
        "overall_risk_reasons": reasons,
    }
