
"""Route calculation and location-based risk endpoints."""

import asyncio
import math
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from geoalchemy2 import Geography
from sqlalchemy import cast, func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..integrations.osrm import OSRMError, get_route
from ..integrations.weather import (
    WeatherForecastError,
    get_weather_forecast,
)
from ..models.segment import RoadSegment
from ..schemas.route import RouteRequest
from ..services.risk_service import assess_segment_risk
from ..services.route_service import assess_route_segments, process_osrm_route


router = APIRouter(tags=["routes"])

RISK_MATCH_RADIUS_M = 100.0


def calculate_bearing_difference(
    segment_bearing: float,
    heading: float,
) -> float:
    """Return the smallest angular difference for a two-way road."""
    forward = abs((segment_bearing - heading + 180) % 360 - 180)
    reverse_bearing = (segment_bearing + 180) % 360
    reverse = abs((reverse_bearing - heading + 180) % 360 - 180)
    return min(forward, reverse)


def calculate_bearing(
    start_lon: float,
    start_lat: float,
    end_lon: float,
    end_lat: float,
) -> float:
    """Calculate the initial bearing from one coordinate to another."""
    lat1 = math.radians(start_lat)
    lat2 = math.radians(end_lat)
    delta_lon = math.radians(end_lon - start_lon)

    y = math.sin(delta_lon) * math.cos(lat2)
    x = (
        math.cos(lat1) * math.sin(lat2)
        - math.sin(lat1)
        * math.cos(lat2)
        * math.cos(delta_lon)
    )
    return (math.degrees(math.atan2(y, x)) + 360) % 360


async def _forecast_for_segment(
    segment: dict,
    arrival_time: datetime,
) -> dict | None:
    """Retrieve forecast data at the midpoint of a route segment."""
    start_lon, start_lat = segment["start"]
    end_lon, end_lat = segment["end"]

    try:
        return await get_weather_forecast(
            latitude=(start_lat + end_lat) / 2,
            longitude=(start_lon + end_lon) / 2,
            arrival_time=arrival_time,
        )
    except WeatherForecastError:
        # Missing weather must not be interpreted as safe weather.
        return None


async def _forecast_route_segments(
    segments: list[dict],
    route_duration_s: float,
    route_distance_m: float,
) -> dict[int, dict | None]:
    """Estimate segment arrival times and fetch their forecasts."""
    if not segments or route_duration_s < 0 or route_distance_m <= 0:
        return {segment["segment_id"]: None for segment in segments}

    total_segment_length = sum(
        float(segment["length_m"]) for segment in segments
    )
    if total_segment_length <= 0:
        return {segment["segment_id"]: None for segment in segments}

    departure_time = datetime.now(timezone.utc)
    cumulative_distance = 0.0
    tasks = []

    for segment in segments:
        cumulative_distance += float(segment["length_m"])
        elapsed_seconds = (
            route_duration_s * cumulative_distance / total_segment_length
        )
        arrival_time = departure_time + timedelta(seconds=elapsed_seconds)

        tasks.append(_forecast_for_segment(segment, arrival_time))

    forecasts = await asyncio.gather(*tasks, return_exceptions=True)

    result: dict[int, dict | None] = {}
    for segment, forecast in zip(segments, forecasts):
        if isinstance(forecast, Exception):
            forecast = None
        result[segment["segment_id"]] = forecast

    return result


@router.post("/route")
async def calculate_route(
    request: RouteRequest,
    db: Annotated[Session, Depends(get_db)],
):
    """Calculate alternative routes and assess their available risk data."""
    origin = (
        request.origin.longitude,
        request.origin.latitude,
    )
    destination = (
        request.destination.longitude,
        request.destination.latitude,
    )

    try:
        data = await get_route(origin, destination, alternatives=True)
        routes = []

        for route in data["routes"]:
            processed = process_osrm_route(route)
            segments = processed["segments"]

            weather_by_segment = await _forecast_route_segments(
                segments,
                processed["duration_s"],
                processed["distance_m"],
            )

            assessed_segments = assess_route_segments(
                db,
                segments,
                weather_by_segment=weather_by_segment,
            )

            for segment in assessed_segments:
                if segment.get("weather_forecast") is None:
                    segment.setdefault("risk_data_gaps", []).append(
                        "Weather forecast is unavailable for the estimated arrival time"
                    )
                else:
                    segment.setdefault("risk_data_gaps", []).append(
                        "Weather risk classification thresholds are not yet confirmed"
                    )

                segment["risk_data_gaps"] = sorted(
                    set(segment.get("risk_data_gaps", []))
                )

            gaps = sorted({
                gap
                for segment in assessed_segments
                for gap in segment.get("risk_data_gaps", [])
            })

            processed["segments"] = assessed_segments
            processed["risk_data_gaps"] = gaps
            processed["risk_assessment"] = (
                "complete"
                if assessed_segments
                and all(
                    segment["risk_assessment"] == "complete"
                    for segment in assessed_segments
                )
                else "incomplete"
            )
            routes.append(processed)

    except OSRMError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Routing service returned an invalid response: {exc}",
        ) from exc

    return {"routes": routes}


@router.get("/risk")
async def get_location_risk(
    lat: float,
    lon: float,
    heading: float | None = None,
    db: Annotated[Session, Depends(get_db)] = None,
):
    """Assess available risk data for the nearest stored road segment."""
    if not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise HTTPException(
            status_code=422,
            detail="Latitude or longitude is outside its valid range.",
        )

    if heading is not None and not 0 <= heading < 360:
        raise HTTPException(
            status_code=422,
            detail="Heading must be between 0 inclusive and 360 exclusive.",
        )

    point = func.ST_SetSRID(
        func.ST_MakePoint(lon, lat),
        4326,
    )
    point_geography = cast(point, Geography(srid=4326))
    road_geography = cast(RoadSegment.geom, Geography(srid=4326))
    distance = func.ST_Distance(road_geography, point_geography)

    match = db.execute(
        select(
            RoadSegment,
            distance.label("distance_m"),
            func.ST_X(func.ST_StartPoint(RoadSegment.geom)).label("start_lon"),
            func.ST_Y(func.ST_StartPoint(RoadSegment.geom)).label("start_lat"),
            func.ST_X(func.ST_EndPoint(RoadSegment.geom)).label("end_lon"),
            func.ST_Y(func.ST_EndPoint(RoadSegment.geom)).label("end_lat"),
        )
        .where(
            func.ST_DWithin(
                road_geography,
                point_geography,
                RISK_MATCH_RADIUS_M,
            )
        )
        .order_by(distance)
        .limit(1)
    ).first()

    if match is None:
        return {
            "latitude": lat,
            "longitude": lon,
            "heading": heading,
            "risk_assessment": "incomplete",
            "risk_score": None,
            "risk_level": None,
            "reasons": [],
            "risk_data_gaps": [
                "No stored road segment found within 100 metres.",
                "Weather, traffic and visibility inputs are unavailable.",
                "Slope threshold has not been confirmed.",
            ],
        }

    road, distance_m, start_lon, start_lat, end_lon, end_lat = match

    segment_bearing = calculate_bearing(
        start_lon,
        start_lat,
        end_lon,
        end_lat,
    )

    heading_difference = (
        calculate_bearing_difference(segment_bearing, heading)
        if heading is not None
        else None
    )

    risk = assess_segment_risk(
        db,
        start=[start_lon, start_lat],
        end=[end_lon, end_lat],
        slope_percent=road.slope_percent,
        slope_threshold_percent=None,
        heavy_rain=None,
        heavy_traffic=None,
        low_visibility=None,
    )

    return {
        "latitude": lat,
        "longitude": lon,
        "heading": heading,
        "road_segment_id": road.id,
        "road_match_distance_m": round(float(distance_m), 2),
        "segment_bearing": round(segment_bearing, 2),
        "heading_difference": (
            round(heading_difference, 2)
            if heading_difference is not None
            else None
        ),
        "risk_assessment": risk["risk_assessment"],
        "risk_score": risk["score"],
        "risk_level": risk["level"],
        "risk_flags": risk["risk_flags"],
        "reasons": risk["reasons"],
        "risk_data_gaps": risk["risk_data_gaps"],
    }
