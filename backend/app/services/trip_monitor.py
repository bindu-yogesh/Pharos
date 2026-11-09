
import asyncio
import logging
import math
from datetime import datetime, timedelta
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import select

from ..database import SessionLocal
from ..integrations.weather import (
    WeatherForecastError,
    get_weather_forecast,
)
from ..models.trip import Trip
from .route_service import assess_route_segments
from .trip_alert_service import (
    check_trip_hazards,
    check_trip_risk_escalation,
)

logger = logging.getLogger(__name__)

MONITOR_INTERVAL_SECONDS = 60
MAX_LOCATION_AGE_MINUTES = 10
MAX_DISTANCE_FROM_ROUTE_M = 500.0
EARTH_RADIUS_M = 6_371_000.0

RISK_LEVEL_ORDER = {
    "Green": 0,
    "Yellow": 1,
    "Orange": 2,
    "Red": 3,
}

scheduler = BackgroundScheduler()


def _point_to_segment_distance_m(
    latitude: float,
    longitude: float,
    start: list[float],
    end: list[float],
) -> float:
    """Approximate distance from a GPS point to a route edge in metres."""

    lat0 = math.radians(latitude)

    def project(coordinate: list[float]) -> tuple[float, float]:
        lon, lat = float(coordinate[0]), float(coordinate[1])
        x = (
            math.radians(lon - longitude)
            * EARTH_RADIUS_M
            * math.cos(lat0)
        )
        y = math.radians(lat - latitude) * EARTH_RADIUS_M
        return x, y

    ax, ay = project(start)
    bx, by = project(end)

    dx = bx - ax
    dy = by - ay
    denominator = dx * dx + dy * dy

    if denominator == 0:
        return math.hypot(ax, ay)

    fraction = max(
        0.0,
        min(1.0, -(ax * dx + ay * dy) / denominator),
    )

    nearest_x = ax + fraction * dx
    nearest_y = ay + fraction * dy

    return math.hypot(nearest_x, nearest_y)


def _distance_to_route_segment(
    latitude: float,
    longitude: float,
    segment: dict[str, Any],
) -> float:
    coordinates = segment.get("coordinates")

    if not isinstance(coordinates, list) or len(coordinates) < 2:
        raise ValueError("Invalid route segment coordinates")

    distances = [
        _point_to_segment_distance_m(
            latitude,
            longitude,
            coordinates[index],
            coordinates[index + 1],
        )
        for index in range(len(coordinates) - 1)
    ]

    return min(distances)


def _get_selected_route(
    route_json: dict[str, Any],
) -> dict[str, Any] | None:
    """Read a selected route, without guessing between alternatives."""

    if isinstance(route_json.get("segments"), list):
        return route_json

    routes = route_json.get("routes")

    if isinstance(routes, list) and len(routes) == 1:
        route = routes[0]
        if isinstance(route, dict):
            return route

    return None


def _get_upcoming_segments(
    trip: Trip,
) -> tuple[list[dict[str, Any]], float] | None:
    """Find the nearest remaining segment using the latest GPS position."""

    if trip.last_latitude is None or trip.last_longitude is None:
        return None

    route = _get_selected_route(trip.route_json or {})

    if route is None:
        logger.warning(
            "Trip %s has no unambiguous selected route",
            trip.id,
        )
        return None

    segments = route.get("segments")

    if not isinstance(segments, list) or not segments:
        logger.warning("Trip %s has no route segments", trip.id)
        return None

    try:
        distances = [
            _distance_to_route_segment(
                float(trip.last_latitude),
                float(trip.last_longitude),
                segment,
            )
            for segment in segments
        ]
    except (TypeError, ValueError, IndexError, KeyError):
        logger.exception(
            "Trip %s contains invalid route geometry",
            trip.id,
        )
        return None

    nearest_index = min(
        range(len(distances)),
        key=distances.__getitem__,
    )

    if distances[nearest_index] > MAX_DISTANCE_FROM_ROUTE_M:
        logger.info(
            "Trip %s is %.1f m from its nearest route segment; "
            "skipping route reassessment",
            trip.id,
            distances[nearest_index],
        )
        return None

    remaining_segments = segments[nearest_index:]

    try:
        total_distance = sum(
            float(segment["length_m"])
            for segment in remaining_segments
        )
        duration_s = float(route["duration_s"])
        route_distance_m = float(route["distance_m"])
    except (KeyError, TypeError, ValueError):
        logger.exception(
            "Trip %s has invalid route distance or duration",
            trip.id,
        )
        return None

    if (
        total_distance <= 0
        or duration_s <= 0
        or route_distance_m <= 0
    ):
        return None

    # Estimate remaining travel time using route average speed.
    # This is not live traffic-based navigation.
    average_speed_mps = route_distance_m / duration_s

    return remaining_segments, average_speed_mps


async def _fetch_weather_for_segments(
    segments: list[dict[str, Any]],
    average_speed_mps: float,
) -> dict[int, dict[str, Any] | None]:
    """Fetch weather at each upcoming segment's estimated arrival time."""

    weather_by_segment: dict[int, dict[str, Any] | None] = {}
    now = datetime.utcnow()
    distance_before_segment = 0.0

    if (
        not math.isfinite(average_speed_mps)
        or average_speed_mps <= 0
    ):
        return {
            int(segment["segment_id"]): None
            for segment in segments
            if segment.get("segment_id") is not None
        }

    async def fetch_one(
        segment: dict[str, Any],
        arrival_time: datetime,
    ) -> tuple[int, dict[str, Any] | None]:
        segment_id = int(segment["segment_id"])
        coordinates = segment["coordinates"]

        # Use the middle coordinate as an approximate segment location.
        midpoint = coordinates[len(coordinates) // 2]
        longitude, latitude = float(midpoint[0]), float(midpoint[1])

        try:
            forecast = await get_weather_forecast(
                latitude=latitude,
                longitude=longitude,
                arrival_time=arrival_time,
            )
            return segment_id, forecast

        except WeatherForecastError as exc:
            logger.warning(
                "Weather unavailable for route segment %s: %s",
                segment_id,
                exc,
            )
            return segment_id, None

        except Exception:
            logger.exception(
                "Weather request failed for route segment %s",
                segment_id,
            )
            return segment_id, None

    tasks = []

    for segment in segments:
        try:
            length_m = float(segment["length_m"])
            segment_id = int(segment["segment_id"])

            if not math.isfinite(length_m) or length_m < 0:
                raise ValueError("Invalid segment length")

            midpoint_distance = distance_before_segment + length_m / 2

            arrival_time = now + timedelta(
                seconds=midpoint_distance / average_speed_mps
            )

            tasks.append(fetch_one(segment, arrival_time))
            distance_before_segment += length_m

        except (KeyError, TypeError, ValueError):
            logger.exception(
                "Invalid segment while estimating weather ETA"
            )

            try:
                weather_by_segment[int(segment.get("segment_id", -1))] = None
            except (TypeError, ValueError):
                continue

    results = await asyncio.gather(*tasks)

    for segment_id, forecast in results:
        weather_by_segment[segment_id] = forecast

    return weather_by_segment


def _assess_upcoming_route(
    db,
    trip: Trip,
) -> None:
    """Reassess upcoming segments and notify on a genuine risk escalation."""

    upcoming = _get_upcoming_segments(trip)

    if upcoming is None:
        return

    segments, average_speed_mps = upcoming

    try:
        weather_by_segment = asyncio.run(
            _fetch_weather_for_segments(
                segments,
                average_speed_mps,
            )
        )

        assessed_segments = assess_route_segments(
            db,
            segments,
            weather_by_segment=weather_by_segment,
        )

        complete_levels = [
            segment.get("level")
            for segment in assessed_segments
            if (
                segment.get("risk_assessment") == "complete"
                and segment.get("score") is not None
                and segment.get("level") in RISK_LEVEL_ORDER
            )
        ]

        # No complete assessment means no escalation notification.
        if not complete_levels:
            logger.info(
                "Trip %s has no completely assessed upcoming segments",
                trip.id,
            )
            return

        # Use the highest risk among complete upcoming segments.
        current_level = max(
            complete_levels,
            key=RISK_LEVEL_ORDER.__getitem__,
        )

        check_trip_risk_escalation(
            db,
            trip,
            current_level,
        )

    except Exception:
        logger.exception(
            "Upcoming route reassessment failed for trip %s",
            trip.id,
        )


def monitor_active_trips() -> None:
    """Check recent locations, route hazards, and upcoming route risk."""

    db = SessionLocal()

    try:
        cutoff = datetime.utcnow() - timedelta(
            minutes=MAX_LOCATION_AGE_MINUTES
        )

        trip_ids = db.scalars(
            select(Trip.id).where(
                Trip.status == "active",
                Trip.last_latitude.is_not(None),
                Trip.last_longitude.is_not(None),
                Trip.last_location_at >= cutoff,
            )
        ).all()

        for trip_id in trip_ids:
            try:
                trip = db.scalar(
                    select(Trip)
                    .where(
                        Trip.id == trip_id,
                        Trip.status == "active",
                    )
                    .with_for_update(skip_locked=True)
                )

                if trip is None:
                    continue

                if (
                    trip.last_location_at is None
                    or trip.last_location_at < cutoff
                ):
                    db.rollback()
                    continue

                # Identify the remaining route from the latest GPS position.
                route_progress = _get_upcoming_segments(trip)

                if route_progress is not None:
                    upcoming_segments, _ = route_progress

                    # Check severe active reports along upcoming route geometry.
                    check_trip_hazards(
                        db,
                        trip,
                        upcoming_segments=upcoming_segments,
                    )
                else:
                    # Fall back to the latest GPS location if route is unavailable.
                    check_trip_hazards(db, trip)

                # Reassess upcoming route segments and weather at ETA.
                _assess_upcoming_route(db, trip)

                db.commit()

            except Exception:
                db.rollback()
                logger.exception(
                    "Failed to monitor trip %s",
                    trip_id,
                )

    except Exception:
        db.rollback()
        logger.exception("Trip monitoring cycle failed")

    finally:
        db.close()


def start_trip_monitor() -> None:
    if scheduler.running:
        return

    scheduler.add_job(
        monitor_active_trips,
        trigger="interval",
        seconds=MONITOR_INTERVAL_SECONDS,
        id="trip_hazard_monitor",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    scheduler.start()
    logger.info("Trip monitor started")


def stop_trip_monitor() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Trip monitor stopped")
