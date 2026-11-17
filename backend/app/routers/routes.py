from math import asin, cos, isfinite, radians, sin, sqrt

import httpx
from fastapi import APIRouter, HTTPException

from risk_engine.score_route import load_route_segments, score_route_segments
from ..schemas.route import RouteRequest, RouteResponse, RiskSegmentResponse

router = APIRouter(prefix="/routes", tags=["Routing and Risk"])

OSRM_URL = "https://router.project-osrm.org/route/v1/driving"
OSRM_TIMEOUT_SECONDS = 15
CORRIDOR_TOLERANCE_METERS = 1500
SEGMENT_MATCH_TOLERANCE_METERS = 250
ROUTE_SAMPLE_SPACING_METERS = 75
EARTH_RADIUS_METERS = 6_371_000


def haversine_distance_m(point_a, point_b):
    lon1, lat1 = point_a
    lon2, lat2 = point_b
    lat1, lat2 = radians(lat1), radians(lat2)
    delta_lat = lat2 - lat1
    delta_lon = radians(lon2 - lon1)
    value = (
        sin(delta_lat / 2) ** 2
        + cos(lat1) * cos(lat2) * sin(delta_lon / 2) ** 2
    )
    return 2 * EARTH_RADIUS_METERS * asin(sqrt(min(1.0, value)))


def identify_corridor_direction(origin, destination, segments):
    if not segments:
        raise HTTPException(status_code=500, detail="Shiradi Ghat route dataset is empty.")

    start, end = segments[0]["start"], segments[-1]["end"]
    origin_point = [origin.longitude, origin.latitude]
    destination_point = [destination.longitude, destination.latitude]

    if (
        haversine_distance_m(origin_point, start) <= CORRIDOR_TOLERANCE_METERS
        and haversine_distance_m(destination_point, end) <= CORRIDOR_TOLERANCE_METERS
    ):
        return "forward"

    if (
        haversine_distance_m(origin_point, end) <= CORRIDOR_TOLERANCE_METERS
        and haversine_distance_m(destination_point, start) <= CORRIDOR_TOLERANCE_METERS
    ):
        return "reverse"

    raise HTTPException(
        status_code=422,
        detail="Risk assessment is currently supported only for the configured Shiradi Ghat corridor.",
    )


def _point_to_segment_distance_m(point, start, end):
    lon, lat = point
    scale_x = EARTH_RADIUS_METERS * cos(radians(lat)) * radians(1)
    scale_y = EARTH_RADIUS_METERS * radians(1)

    ax = (start[0] - lon) * scale_x
    ay = (start[1] - lat) * scale_y
    bx = (end[0] - lon) * scale_x
    by = (end[1] - lat) * scale_y

    dx, dy = bx - ax, by - ay
    length_squared = dx * dx + dy * dy

    if length_squared == 0:
        return sqrt(ax * ax + ay * ay)

    projection = max(
        0.0,
        min(1.0, -(ax * dx + ay * dy) / length_squared),
    )
    nearest_x = ax + projection * dx
    nearest_y = ay + projection * dy
    return sqrt(nearest_x * nearest_x + nearest_y * nearest_y)


def _sample_route_geometry(coordinates, spacing_m=ROUTE_SAMPLE_SPACING_METERS):
    if not isinstance(coordinates, list) or len(coordinates) < 2:
        raise ValueError("OSRM route geometry must contain at least two coordinates")

    for coordinate in coordinates:
        if (
            not isinstance(coordinate, (list, tuple))
            or len(coordinate) < 2
            or not all(
                isinstance(value, (int, float))
                and not isinstance(value, bool)
                and isfinite(value)
                for value in coordinate[:2]
            )
        ):
            raise ValueError("OSRM route geometry contains an invalid coordinate")

        lon, lat = coordinate[:2]
        if not -180 <= lon <= 180 or not -90 <= lat <= 90:
            raise ValueError("OSRM route geometry contains an out-of-range coordinate")

    samples = []

    for start, end in zip(coordinates, coordinates[1:]):
        start = [float(start[0]), float(start[1])]
        end = [float(end[0]), float(end[1])]
        distance = haversine_distance_m(start, end)
        steps = max(1, int(distance / spacing_m) + 1)

        for index in range(steps):
            fraction = index / steps
            samples.append([
                start[0] + (end[0] - start[0]) * fraction,
                start[1] + (end[1] - start[1]) * fraction,
            ])

    samples.append([float(coordinates[-1][0]), float(coordinates[-1][1])])
    return samples


def match_route_to_segments(
    route_coordinates,
    segments,
    max_distance_m=SEGMENT_MATCH_TOLERANCE_METERS,
):
    if (
        not isinstance(max_distance_m, (int, float))
        or isinstance(max_distance_m, bool)
        or not isfinite(max_distance_m)
        or max_distance_m <= 0
    ):
        raise ValueError("max_distance_m must be a positive finite number")

    samples = _sample_route_geometry(route_coordinates)

    if not segments:
        return []

    ordered_ids = []

    for point in samples:
        nearest_id = None
        nearest_distance = float("inf")

        for segment in segments:
            distance = _point_to_segment_distance_m(
                point, segment["start"], segment["end"]
            )
            if distance < nearest_distance:
                nearest_distance = distance
                nearest_id = segment["segment_id"]

        if (
            nearest_distance <= max_distance_m
            and (not ordered_ids or ordered_ids[-1] != nearest_id)
        ):
            ordered_ids.append(nearest_id)

    return list(dict.fromkeys(ordered_ids))


@router.post("/assess", response_model=RouteResponse)
def assess_route(request: RouteRequest):
    route_segments = load_route_segments()

    direction = identify_corridor_direction(
        request.origin, request.destination, route_segments
    )

    coordinates = (
        f"{request.origin.longitude},{request.origin.latitude};"
        f"{request.destination.longitude},{request.destination.latitude}"
    )

    try:
        response = httpx.get(
            f"{OSRM_URL}/{coordinates}",
            params={
                "overview": "full",
                "geometries": "geojson",
                "steps": "false",
            },
            timeout=OSRM_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()

    except httpx.TimeoutException as error:
        raise HTTPException(status_code=504, detail="OSRM routing service timed out.") from error
    except httpx.RequestError as error:
        raise HTTPException(status_code=503, detail="Unable to connect to OSRM.") from error
    except httpx.HTTPStatusError as error:
        raise HTTPException(status_code=502, detail="OSRM returned an unsuccessful response.") from error

    if (
        not isinstance(data, dict)
        or data.get("code") != "Ok"
        or not isinstance(data.get("routes"), list)
        or not data["routes"]
    ):
        raise HTTPException(status_code=502, detail="OSRM could not calculate this route.")

    osrm_route = data["routes"][0]

    try:
        if not isinstance(osrm_route, dict):
            raise ValueError("OSRM route must be an object")

        for metric in ("distance", "duration"):
            value = osrm_route.get(metric)
            if (
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not isfinite(value)
                or value < 0
            ):
                raise ValueError(
                    f"OSRM route {metric} must be a non-negative finite number"
                )

        geometry = osrm_route["geometry"]
        if not isinstance(geometry, dict) or geometry.get("type") != "LineString":
            raise ValueError("OSRM did not return a GeoJSON LineString")

        matched_ids = match_route_to_segments(
            geometry.get("coordinates"), route_segments
        )
        if not matched_ids:
            raise ValueError("OSRM route does not match the configured Shiradi Ghat segments")

        scored_segments = score_route_segments(
            district=request.district,
            observation_date=(
                request.observation_date.isoformat()
                if request.observation_date else None
            ),
            include_live_data=request.include_live_data,
            route_duration_s=osrm_route.get("duration"),
            reverse=direction == "reverse",
        )

    except (ValueError, OSError, KeyError, TypeError) as error:
        raise HTTPException(
            status_code=502,
            detail=f"Unable to match or score route: {error}",
        ) from error

    score_lookup = {
        item["segment_id"]: item for item in scored_segments
    }
    route_lookup = {
        item["segment_id"]: item for item in route_segments
    }

    risk_segments = []

    for segment_id in matched_ids:
        scored = score_lookup.get(segment_id)
        if scored is None:
            continue

        route_segment = route_lookup[segment_id]
        start, end = route_segment["start"], route_segment["end"]

        risk_segments.append(
            RiskSegmentResponse(
                segment_id=segment_id,
                risk_score=scored["risk_score"],
                risk_level=scored["risk_level"],
                known_risk_score=scored["known_risk_score"],
                risk_status=scored["risk_status"],
                missing_factors=scored["missing_factors"],
                reasons=scored["reasons"],
                latitude=(start[1] + end[1]) / 2,
                longitude=(start[0] + end[0]) / 2,
                visibility_m=scored.get("visibility_m"),
                traffic=scored.get("traffic"),
                historical_incident_ids=scored.get("historical_incident_ids") or [],
                recent_hazard_report_ids=scored.get("recent_hazard_report_ids") or [],
                data_sources=scored.get("data_sources") or {},
            )
        )

    if not risk_segments:
        raise HTTPException(status_code=502, detail="No scored segments matched the OSRM route.")

    return RouteResponse(
        distance_m=osrm_route.get("distance"),
        duration_s=osrm_route.get("duration"),
        district=request.district,
        rainfall_mm=next(
            (score_lookup[segment_id]["rainfall_mm"] for segment_id in matched_ids
             if score_lookup.get(segment_id)
             and score_lookup[segment_id]["rainfall_mm"] is not None),
            None,
        ),
        weather_observation_date=next(
            (score_lookup[segment_id]["weather_observation_date"] for segment_id in matched_ids
             if score_lookup.get(segment_id)
             and score_lookup[segment_id]["weather_observation_date"] is not None),
            None,
        ),
        segments=risk_segments,
    )
