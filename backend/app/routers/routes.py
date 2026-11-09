
"""Route calculation and location-based risk endpoints."""

import asyncio
import json
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
from ..schemas.route import RouteRequest, RouteCollectionResponse
from ..services.risk_service import assess_segment_risk
from ..services.route_service import (
    assess_route_segments,
    calculate_overall_route_risk,
    classify_weather_risk,
    process_osrm_route,
)


router = APIRouter(tags=["routes"])


# Location-based risk configuration.
RISK_MATCH_RADIUS_M = 100.0
RISK_LOOKAHEAD_RADIUS_M = 1000.0
MAX_FORWARD_SEGMENTS = 10
MAX_HEADING_DIFFERENCE = 45.0
MAX_FORWARD_POSITION_ANGLE = 90.0
SLOPE_THRESHOLD_PERCENT = 6.0

RISK_COLORS = {
    "Green": "green",
    "Yellow": "yellow",
    "Orange": "orange",
    "Red": "red",
}


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
        return {
            segment["segment_id"]: None
            for segment in segments
        }

    total_segment_length = sum(
        float(segment["length_m"])
        for segment in segments
    )

    if total_segment_length <= 0:
        return {
            segment["segment_id"]: None
            for segment in segments
        }

    departure_time = datetime.now(timezone.utc)
    cumulative_distance = 0.0
    tasks = []

    for segment in segments:
        cumulative_distance += float(segment["length_m"])

        elapsed_seconds = (
            route_duration_s
            * cumulative_distance
            / total_segment_length
        )

        arrival_time = departure_time + timedelta(
            seconds=elapsed_seconds
        )

        tasks.append(
            _forecast_for_segment(segment, arrival_time)
        )

    forecasts = await asyncio.gather(
        *tasks,
        return_exceptions=True,
    )

    result: dict[int, dict | None] = {}

    for segment, forecast in zip(segments, forecasts):
        if isinstance(forecast, Exception):
            forecast = None

        result[segment["segment_id"]] = forecast

    return result


@router.post(
    "/route",
    response_model=RouteCollectionResponse,
)
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
        # Step 1: Request alternative routes from OSRM.
        data = await get_route(
            origin,
            destination,
            alternatives=True,
        )

        routes = []

        for route in data["routes"]:

            # Step 2: Normalize the OSRM route.
            processed = process_osrm_route(route)

            segments = processed["segments"]

            # Step 3: Get weather forecasts at estimated arrival times.
            weather_by_segment = await _forecast_route_segments(
                segments,
                processed["duration_s"],
                processed["distance_m"],
            )

            # Step 4: Assess individual route segments.
            assessed_segments = assess_route_segments(
                db,
                segments,
                weather_by_segment=weather_by_segment,
            )

            # Step 5: Remove duplicate risk-data-gap messages.
            for segment in assessed_segments:
                segment["risk_data_gaps"] = sorted(
                    set(segment.get("risk_data_gaps", []))
                )

            # Step 6: Calculate distance-weighted overall risk.
            overall_risk = calculate_overall_route_risk(
                assessed_segments
            )

            # Step 7: Collect all segment-level data gaps.
            route_gaps = sorted({
                gap
                for segment in assessed_segments
                for gap in segment.get("risk_data_gaps", [])
            })

            # Step 8: Construct the final route response.
            processed["segments"] = assessed_segments
            processed["risk_data_gaps"] = route_gaps

            processed.update(overall_risk)

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
    """Assess multiple stored road segments around and ahead of the user."""

    # Step 1: Validate geographical coordinates.
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

    # Step 2: Create the user's current location point.
    point = func.ST_SetSRID(
        func.ST_MakePoint(lon, lat),
        4326,
    )

    point_geography = cast(
        point,
        Geography(srid=4326),
    )

    road_geography = cast(
        RoadSegment.geom,
        Geography(srid=4326),
    )

    distance = func.ST_Distance(
        road_geography,
        point_geography,
    )

    # Find the midpoint of each road for forward-position filtering.
    midpoint = func.ST_LineInterpolatePoint(
        RoadSegment.geom,
        0.5,
    )

    # Step 3: Retrieve nearby road segments.
    matches = db.execute(
        select(
            RoadSegment,
            distance.label("distance_m"),
            func.ST_X(
                func.ST_StartPoint(RoadSegment.geom)
            ).label("start_lon"),
            func.ST_Y(
                func.ST_StartPoint(RoadSegment.geom)
            ).label("start_lat"),
            func.ST_X(
                func.ST_EndPoint(RoadSegment.geom)
            ).label("end_lon"),
            func.ST_Y(
                func.ST_EndPoint(RoadSegment.geom)
            ).label("end_lat"),
            func.ST_X(midpoint).label("mid_lon"),
            func.ST_Y(midpoint).label("mid_lat"),
            func.ST_AsGeoJSON(
                RoadSegment.geom
            ).label("geometry"),
        )
        .where(
            func.ST_DWithin(
                road_geography,
                point_geography,
                RISK_LOOKAHEAD_RADIUS_M,
            )
        )
        .order_by(distance)
        .limit(100)
    ).all()

    # Step 4: Filter candidate roads using heading.
    candidates = []

    for match in matches:
        (
            road,
            distance_m,
            start_lon,
            start_lat,
            end_lon,
            end_lat,
            mid_lon,
            mid_lat,
            geometry_json,
        ) = match

        segment_bearing = calculate_bearing(
            start_lon,
            start_lat,
            end_lon,
            end_lat,
        )

        heading_difference = (
            calculate_bearing_difference(
                segment_bearing,
                heading,
            )
            if heading is not None
            else None
        )

        # Reject roads that do not approximately align
        # with the user's direction.
        if (
            heading_difference is not None
            and heading_difference > MAX_HEADING_DIFFERENCE
        ):
            continue

        # Calculate the direction from the user to the road midpoint.
        position_bearing = calculate_bearing(
            lon,
            lat,
            mid_lon,
            mid_lat,
        )

        position_difference = (
            abs(
                (position_bearing - heading + 180) % 360 - 180
            )
            if heading is not None
            else None
        )

        # Allow roads immediately underneath the user.
        # Filter out roads substantially behind the user.
        if (
            heading is not None
            and float(distance_m) > RISK_MATCH_RADIUS_M
            and position_difference > MAX_FORWARD_POSITION_ANGLE
        ):
            continue

        try:
            geometry = (
                json.loads(geometry_json)
                if geometry_json
                else None
            )
        except (TypeError, ValueError):
            geometry = None

        candidates.append({
            "road": road,
            "distance_m": float(distance_m),
            "start": [start_lon, start_lat],
            "end": [end_lon, end_lat],
            "bearing": segment_bearing,
            "heading_difference": heading_difference,
            "position_difference": position_difference,
            "geometry": geometry,
        })

    # Step 5: Keep the closest suitable road segments.
    candidates.sort(
        key=lambda item: item["distance_m"]
    )

    candidates = candidates[:MAX_FORWARD_SEGMENTS]

    # Step 6: Return a clear incomplete response when no road is found.
    if not candidates:
        return {
            "latitude": lat,
            "longitude": lon,
            "heading": heading,
            "risk_assessment": "incomplete",
            "risk_score": None,
            "risk_level": None,
            "risk_flags": None,
            "reasons": [],
            "segments": [],
            "risk_data_gaps": [
                "No stored road segment found within the look-ahead radius.",
                "Weather, traffic and visibility inputs are unavailable.",
            ],
        }

    # Step 7: Fetch current weather forecasts for selected segments.
    forecast_time = datetime.now(timezone.utc)

    weather_forecasts = await asyncio.gather(
        *[
            _forecast_for_segment(candidate, forecast_time)
            for candidate in candidates
        ],
        return_exceptions=True,
    )

    # Step 8: Assess each selected road segment.
    assessed_segments = []

    for candidate, weather in zip(candidates, weather_forecasts):
        if isinstance(weather, Exception):
            weather = None

        heavy_rain, low_visibility = classify_weather_risk(weather)

        road = candidate["road"]

        risk = assess_segment_risk(
            db,
            start=candidate["start"],
            end=candidate["end"],
            slope_percent=road.slope_percent,
            slope_threshold_percent=SLOPE_THRESHOLD_PERCENT,
            heavy_rain=heavy_rain,
            heavy_traffic=None,
            low_visibility=low_visibility,
        )

        assessed_segments.append({
            "road_segment_id": road.id,
            "distance_from_user_m": round(
                candidate["distance_m"],
                2,
            ),
            "geometry": candidate["geometry"],
            "segment_bearing": round(
                candidate["bearing"],
                2,
            ),
            "heading_difference": (
                round(candidate["heading_difference"], 2)
                if candidate["heading_difference"] is not None
                else None
            ),
            "weather_forecast": weather,
            "risk_assessment": risk["risk_assessment"],
            "risk_score": risk["score"],
            "risk_level": risk["level"],
            "risk_color": RISK_COLORS.get(risk["level"]),
            "risk_flags": risk["risk_flags"],
            "reasons": risk["reasons"],
            "risk_data_gaps": risk["risk_data_gaps"],
        })

    # Step 9: Preserve the original top-level response fields.
    nearest = assessed_segments[0]

    all_gaps = sorted({
        gap
        for segment in assessed_segments
        for gap in segment["risk_data_gaps"]
    })

    overall_assessment = (
        "complete"
        if all(
            segment["risk_assessment"] == "complete"
            for segment in assessed_segments
        )
        else "incomplete"
    )

    return {
        "latitude": lat,
        "longitude": lon,
        "heading": heading,
        "road_segment_id": nearest["road_segment_id"],
        "road_match_distance_m": nearest["distance_from_user_m"],
        "segment_bearing": nearest["segment_bearing"],
        "heading_difference": nearest["heading_difference"],
        "risk_assessment": overall_assessment,
        "risk_score": nearest["risk_score"],
        "risk_level": nearest["risk_level"],
        "risk_flags": nearest["risk_flags"],
        "reasons": nearest["reasons"],
        "segments": assessed_segments,
        "risk_data_gaps": all_gaps,
    }
