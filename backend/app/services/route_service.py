
"""Route processing built on the existing OSRM integration."""

from typing import Any

from geoalchemy2 import Geography
from sqlalchemy import cast, func, select
from sqlalchemy.orm import Session

from ..models.segment import RoadSegment
from .risk_service import assess_segment_risk

SEGMENT_MATCH_RADIUS_M = 100.0


def create_segments(
    coordinates: list[list[float]],
    edge_distances: list[float],
    target_length_m: float = 1000,
) -> list[dict[str, Any]]:
    """Group consecutive OSRM edges into approximately 1 km segments.

    Coordinates use OSRM GeoJSON order: [longitude, latitude].
    Edge distances are the road distances returned by OSRM annotations.
    """
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
    segment_start = coordinates[0]
    segment_distance = 0.0
    segment_id = 1

    for index, distance in enumerate(edge_distances):
        segment_distance += distance
        edge_end = coordinates[index + 1]

        if segment_distance >= target_length_m:
            segments.append({
                "segment_id": segment_id,
                "start": segment_start,
                "end": edge_end,
                "length_m": round(segment_distance, 2),
                "risk_status": "not_assessed",
            })
            segment_id += 1
            segment_start = edge_end
            segment_distance = 0.0

    if segment_distance > 0:
        segments.append({
            "segment_id": segment_id,
            "start": segment_start,
            "end": coordinates[-1],
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
        annotations = [leg["annotation"]["distance"] for leg in legs]
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(
            "OSRM route is missing geometry, distance, duration, or annotations"
        ) from exc

    if len(legs) != 1:
        raise ValueError(
            "Expected one OSRM leg for the requested origin and destination"
        )

    if not isinstance(coordinates, list) or not annotations:
        raise ValueError("OSRM geometry and distance annotations must be lists")

    if not isinstance(annotations[0], list):
        raise ValueError("OSRM distance annotations must be a list")

    segments = create_segments(coordinates, annotations[0])

    return {
        "distance_m": distance_m,
        "duration_s": duration_s,
        "geometry": route["geometry"],
        "segments": segments,
        "risk_assessment": "unavailable",
        "risk_data_gaps": [
            "Live segment slope/elevation is not yet available for arbitrary routes",
            "Per-segment incident proximity is not yet integrated",
            "Weather forecast at each segment's expected arrival time is not yet integrated",
            "Traffic and visibility inputs are not yet integrated",
        ],
    }


def assess_route_segments(
    db: Session,
    segments: list[dict[str, Any]],
    weather_by_segment: dict[int, dict[str, Any] | None] | None = None,
) -> list[dict[str, Any]]:
    """Match route segments to stored roads and assess available risk data.

    Weather forecasts are attached to segments for downstream use.
    Weather risk flags remain unset until classification thresholds are agreed.
    """
    weather_by_segment = weather_by_segment or {}
    assessed: list[dict[str, Any]] = []

    for segment in segments:
        start = segment["start"]
        end = segment["end"]
        weather = weather_by_segment.get(segment["segment_id"])

        route_line = func.ST_GeomFromText(
            (
                f"LINESTRING({float(start[0])} {float(start[1])},"
                f"{float(end[0])} {float(end[1])})"
            ),
            4326,
        )
        route_geography = cast(route_line, Geography(srid=4326))
        road_geography = cast(RoadSegment.geom, Geography(srid=4326))

        distance = func.ST_Distance(road_geography, route_geography)

        match = db.execute(
            select(RoadSegment, distance.label("distance_m"))
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

        if match is None:
            assessed.append({
                **segment,
                "risk_status": "incomplete",
                "road_segment_id": None,
                "risk_assessment": "incomplete",
                "weather_forecast": weather,
                "score": None,
                "level": None,
                "reasons": [],
                "risk_data_gaps": [
                    "No stored road segment matched within the configured radius",
                    "Slope threshold has not been confirmed",
                    (
                        "Weather forecast unavailable for this segment"
                        if weather is None
                        else
                        "Weather risk classification thresholds are not yet confirmed"
                    ),
                    "Traffic and visibility inputs are unavailable",
                ],
            })
            continue

        road, distance_m = match

        risk = assess_segment_risk(
            db,
            start,
            end,
            slope_percent=road.slope_percent,
            # Deliberately unset until the threshold is agreed with Bindu.
            slope_threshold_percent=None,
            # Do not classify raw weather data without agreed thresholds.
            heavy_rain=None,
            heavy_traffic=None,
            low_visibility=None,
        )

        risk_data_gaps = list(risk["risk_data_gaps"])

        if weather is None:
            risk_data_gaps.append(
                "Weather forecast unavailable for this segment"
            )
        else:
            risk_data_gaps.append(
                "Weather risk classification thresholds are not yet confirmed"
            )

        assessed.append({
            **segment,
            "risk_status": risk["risk_assessment"],
            "road_segment_id": road.id,
            "road_match_distance_m": round(float(distance_m), 2),
            "slope_percent": road.slope_percent,
            "weather_forecast": weather,
            "risk_assessment": risk["risk_assessment"],
            "risk_flags": risk["risk_flags"],
            "risk_data_gaps": risk_data_gaps,
            "score": risk["score"],
            "level": risk["level"],
            "reasons": risk["reasons"],
        })

    return assessed
