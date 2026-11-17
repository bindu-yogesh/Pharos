import logging
import os
from datetime import datetime, timedelta
from math import isfinite
from threading import Lock
from time import monotonic
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy import text

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
TOMTOM_URL = "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/16/json"
TIMEOUT = 8
LOCAL_TZ = ZoneInfo("Asia/Kolkata")
HEAVY_RAIN_MM_PER_HOUR = 7.5
LOW_VISIBILITY_METERS = 1000.0
TRAFFIC_SPEED_RATIO = 0.50
MIN_TRAFFIC_CONFIDENCE = 0.50
RECENT_HAZARD_DAYS = 30
RECENT_HAZARD_RADIUS_METERS = 500.0

logger = logging.getLogger(__name__)

_cache = {}
_cache_lock = Lock()


def _valid_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and isfinite(value)
    )


def fetch_weather_for_segments(segments, arrival_times, client=httpx):
    """Fetch hourly precipitation and visibility for all segment ETAs."""
    if not segments or len(segments) != len(arrival_times):
        return [None] * len(segments)

    points = [
        (
            (item["start"][1] + item["end"][1]) / 2,
            (item["start"][0] + item["end"][0]) / 2,
        )
        for item in segments
    ]
    params = {
        "latitude": ",".join(f"{lat:.6f}" for lat, _ in points),
        "longitude": ",".join(f"{lon:.6f}" for _, lon in points),
        "hourly": "precipitation,visibility",
        "forecast_days": 2,
        "timezone": "Asia/Kolkata",
    }

    try:
        response = client.get(OPEN_METEO_URL, params=params, timeout=TIMEOUT)
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError, TypeError):
        return [None] * len(segments)

    locations = payload if isinstance(payload, list) else [payload]
    if len(locations) != len(segments):
        return [None] * len(segments)

    results = []
    for location, eta in zip(locations, arrival_times):
        try:
            hourly = location["hourly"]
            times = hourly["time"]
            rain = hourly["precipitation"]
            visibility = hourly["visibility"]
            if not (len(times) == len(rain) == len(visibility)):
                results.append(None)
                continue

            target = eta.astimezone(LOCAL_TZ).replace(tzinfo=None)
            choices = [
                (abs((datetime.fromisoformat(value) - target).total_seconds()), i)
                for i, value in enumerate(times)
            ]
            delta, index = min(choices)
            if delta > 90 * 60:
                results.append(None)
                continue

            rain_value, visibility_value = rain[index], visibility[index]
            if not _valid_number(rain_value) or not _valid_number(visibility_value):
                results.append(None)
                continue

            results.append({
                "precipitation_mm": float(rain_value),
                "visibility_m": float(visibility_value),
                "heavy_rain": float(rain_value) >= HEAVY_RAIN_MM_PER_HOUR,
                "low_visibility": float(visibility_value) <= LOW_VISIBILITY_METERS,
                "forecast_time": times[index],
                "source": "Open-Meteo",
            })
        except (KeyError, TypeError, ValueError, IndexError):
            results.append(None)

    return results


def fetch_traffic_for_segment(latitude, longitude, client=httpx):
    """Return confidence-qualified TomTom flow data, or None if unavailable."""
    api_key = os.getenv("TOMTOM_API_KEY")
    if not api_key:
        return None

    cache_key = (round(float(latitude), 4), round(float(longitude), 4))
    now = monotonic()
    with _cache_lock:
        cached = _cache.get(cache_key)
        if cached and now - cached[0] < 120:
            return cached[1]

    result = None
    try:
        response = client.get(
            TOMTOM_URL,
            params={
                "key": api_key,
                "point": f"{latitude:.6f},{longitude:.6f}",
                "unit": "kmph",
            },
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        body = response.json()["flowSegmentData"]
        current = body["currentSpeed"]
        free_flow = body["freeFlowSpeed"]
        confidence = body["confidence"]
        closure = body.get("roadClosure", False)

        if (
            _valid_number(current)
            and _valid_number(free_flow)
            and _valid_number(confidence)
            and free_flow > 0
            and MIN_TRAFFIC_CONFIDENCE <= confidence <= 1
            and isinstance(closure, bool)
        ):
            result = {
                "heavy_traffic": closure or current / free_flow <= TRAFFIC_SPEED_RATIO,
                "current_speed_kmph": float(current),
                "free_flow_speed_kmph": float(free_flow),
                "confidence": float(confidence),
                "road_closure": closure,
                "source": "TomTom Traffic",
                "observed_at": datetime.now(LOCAL_TZ).isoformat(),
            }
    except (httpx.HTTPError, KeyError, TypeError, ValueError, AttributeError, IndexError):
        logger.warning("TomTom traffic data unavailable for segment (%s, %s)", latitude, longitude)
        result = None

    with _cache_lock:
        _cache[cache_key] = (now, result)
    return result


def fetch_recent_hazard_matches(segments, now=None):
    """Map active reports from the last 30 days to nearby route segments."""
    try:
        from backend.app.database import SessionLocal
        current = now or datetime.now(LOCAL_TZ).astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
        if current.tzinfo is not None:
            current = current.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)
        since = current - timedelta(days=RECENT_HAZARD_DAYS)
        statement = text("""
            SELECT id, type, ST_Y(geom) AS latitude, ST_X(geom) AS longitude
            FROM reports
            WHERE status = 'active'
              AND type IN ('landslide', 'falling_rock', 'blockage')
              AND geom IS NOT NULL
              AND created_at >= :since
              AND (expires_at IS NULL OR expires_at > :now)
        """)
        with SessionLocal() as session:
            rows = session.execute(
                statement, {"since": since, "now": current}
            ).mappings().all()

        reports = [
            {
                "id": str(row["id"]),
                "type": str(row["type"]),
                "latitude": float(row["latitude"]),
                "longitude": float(row["longitude"]),
            }
            for row in rows
        ]
        from risk_engine.incident_matching import match_incidents_to_segments
        return match_incidents_to_segments(
            reports, segments, max_distance_m=RECENT_HAZARD_RADIUS_METERS
        )
    except Exception:
        # A database failure is unknown, never evidence that no hazard exists.
        logger.exception("Unable to retrieve recent community hazard reports")
        return None
