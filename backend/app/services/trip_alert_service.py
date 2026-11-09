from datetime import datetime

from geoalchemy2 import Geography
from sqlalchemy import cast, func, or_, select
from sqlalchemy.orm import Session

from ..integrations.fcm import send
from ..models.device import DeviceToken
from ..models.report import Report
from ..models.trip import Trip



ALERT_RADIUS_M = 500.0
ALERTABLE_TYPES = ("landslide", "falling_rock")



def check_trip_hazards(
    db: Session,
    trip: Trip,
    upcoming_segments: list[dict] | None = None,
) -> int:
    """
    Find severe active hazards near upcoming route segments.
    Falls back to the latest GPS location when no route is supplied.
    Notify only once per report per trip.
    """

    report_geography = cast(
        Report.geom,
        Geography(srid=4326),
    )

    hazard_conditions = []

    if upcoming_segments:
        for segment in upcoming_segments:
            coordinates = segment.get("coordinates", [])

            if not isinstance(coordinates, list) or len(coordinates) < 2:
                continue

            valid_coordinates = []

            for coordinate in coordinates:
                try:
                    lon, lat = float(coordinate[0]), float(coordinate[1])
                except (TypeError, ValueError, IndexError):
                    continue

                if not (math.isfinite(lon) and math.isfinite(lat)):
                    continue

                if not (-180 <= lon <= 180 and -90 <= lat <= 90):
                    continue

                valid_coordinates.append((lon, lat))

            if len(valid_coordinates) < 2:
                continue

            wkt_coordinates = ", ".join(
                f"{lon} {lat}" for lon, lat in valid_coordinates
            )
            line_wkt = f"LINESTRING({wkt_coordinates})"

            route_line = func.ST_GeomFromText(line_wkt, 4326)
            route_geography = cast(
                route_line,
                Geography(srid=4326),
            )

            hazard_conditions.append(
                func.ST_DWithin(
                    report_geography,
                    route_geography,
                    ALERT_RADIUS_M,
                )
            )

    # Backward-compatible fallback for callers without route segments.
    if not hazard_conditions:
        if trip.last_latitude is None or trip.last_longitude is None:
            return 0

        point = func.ST_SetSRID(
            func.ST_MakePoint(
                trip.last_longitude,
                trip.last_latitude,
            ),
            4326,
        )

        point_geography = cast(
            point,
            Geography(srid=4326),
        )

        hazard_conditions.append(
            func.ST_DWithin(
                report_geography,
                point_geography,
                ALERT_RADIUS_M,
            )
        )

    now = datetime.utcnow()

    reports = db.scalars(
        select(Report).where(
            Report.status == "active",
            Report.type.in_(ALERTABLE_TYPES),
            Report.severity >= 2,
            or_(
                Report.expires_at.is_(None),
                Report.expires_at > now,
            ),
            Report.geom.is_not(None),
            or_(*hazard_conditions),
        )
    ).all()

    already_alerted = set(trip.alerted_report_ids or [])

    new_reports = [
        report for report in reports
        if report.id not in already_alerted
    ]

    if not new_reports:
        return 0

    tokens = db.scalars(
        select(DeviceToken.fcm_token).where(
            DeviceToken.user_id == trip.user_id
        )
    ).all()

    if not tokens:
        return 0

    successful_alerts = 0

    for report in new_reports:
        title = "Hazard ahead"
        body = (
            f"{report.type.replace('_', ' ').title()} reported "
            "within 500 metres of your upcoming route. "
            "Please proceed carefully."
        )

        sent = False

        for token in tokens:
            try:
                if send(token, title, body):
                    sent = True
            except Exception:
                continue

        if sent:
            already_alerted.add(report.id)
            successful_alerts += 1

    trip.alerted_report_ids = sorted(already_alerted)

    return successful_alerts



RISK_LEVEL_ORDER = {
    "Green": 0,
    "Yellow": 1,
    "Orange": 2,
    "Red": 3,
}



def check_trip_risk_escalation(
    db: Session,
    trip: Trip,
    current_level: str | None,
) -> bool:
    """Notify when a complete risk assessment shows an upward transition."""

    if current_level not in RISK_LEVEL_ORDER:
        return False

    previous_level = trip.last_alerted_level

    if previous_level not in RISK_LEVEL_ORDER:
        previous_level = "Green"

    current_rank = RISK_LEVEL_ORDER[current_level]
    previous_rank = RISK_LEVEL_ORDER[previous_level]

    # Update the baseline on downgrade without sending an alert.
    if current_rank < previous_rank:
        trip.last_alerted_level = current_level
        return False

    if current_rank == previous_rank:
        return False

    tokens = db.scalars(
        select(DeviceToken.fcm_token).where(
            DeviceToken.user_id == trip.user_id
        )
    ).all()

    if not tokens:
        return False

    title = f"Route risk increased to {current_level}"
    body = (
        f"Risk on your selected route has increased "
        f"from {previous_level} to {current_level}. "
        "Please proceed carefully."
    )

    sent = False

    for token in tokens:
        try:
            if send(token, title, body):
                sent = True
        except Exception:
            continue

    if sent:
        trip.last_alerted_level = current_level
        return True

    return False
