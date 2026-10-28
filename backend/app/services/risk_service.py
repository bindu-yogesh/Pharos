
"""Database-backed risk flags for a route segment."""

from datetime import datetime
from typing import Any

from geoalchemy2 import Geography
from sqlalchemy import cast, func, or_, select
from sqlalchemy.orm import Session

from ..models.incident import IncidentHistory
from ..models.report import Report
from risk_engine.scorer import calculate_risk


DEFAULT_PROXIMITY_M = 500.0


def assess_segment_risk(
    db: Session,
    start: list[float],
    end: list[float],
    *,
    slope_percent: float | None = None,
    slope_threshold_percent: float | None = None,
    heavy_rain: bool | None = None,
    low_visibility: bool | None = None,
    heavy_traffic: bool | None = None,
    proximity_m: float = DEFAULT_PROXIMITY_M,
) -> dict[str, Any]:
    """Assess a segment without treating unknown inputs as safe."""
    if proximity_m <= 0:
        raise ValueError("proximity_m must be greater than zero")

    if len(start) != 2 or len(end) != 2:
        raise ValueError("Segment endpoints must be [longitude, latitude]")

    wkt = (
        f"LINESTRING({float(start[0])} {float(start[1])},"
        f"{float(end[0])} {float(end[1])})"
    )
    segment_geom = func.ST_GeomFromText(wkt, 4326)
    segment_geography = cast(segment_geom, Geography(srid=4326))

    incident_nearby = db.scalar(
        select(IncidentHistory.id)
        .where(
            IncidentHistory.geom.is_not(None),
            func.lower(IncidentHistory.type).contains("landslide"),
            func.ST_DWithin(
                cast(IncidentHistory.geom, Geography(srid=4326)),
                segment_geography,
                proximity_m,
            ),
        )
        .limit(1)
    ) is not None

    now = datetime.utcnow()
    hazard_nearby = db.scalar(
        select(Report.id)
        .where(
            Report.geom.is_not(None),
            Report.status == "active",
            Report.type.in_(["landslide", "falling_rock"]),
            or_(Report.expires_at.is_(None), Report.expires_at > now),
            func.ST_DWithin(
                cast(Report.geom, Geography(srid=4326)),
                segment_geography,
                proximity_m,
            ),
        )
        .limit(1)
    ) is not None

    steep_slope: bool | None = None
    if slope_percent is not None and slope_threshold_percent is not None:
        if slope_threshold_percent <= 0:
            raise ValueError(
                "slope_threshold_percent must be greater than zero"
            )
        steep_slope = abs(slope_percent) > slope_threshold_percent

    flags = {
        "heavy_rain": heavy_rain,
        "landslide_history": incident_nearby,
        "steep_slope": steep_slope,
        "recent_hazard_report": hazard_nearby,
        "heavy_traffic": heavy_traffic,
        "low_visibility": low_visibility,
    }

    missing_inputs = [
        name for name, value in flags.items() if value is None
    ]

    result: dict[str, Any] = {
        "risk_assessment": (
            "complete" if not missing_inputs else "incomplete"
        ),
        "risk_flags": flags,
        "risk_data_gaps": missing_inputs,
        "proximity_m": proximity_m,
    }

    if not missing_inputs:
        result.update(calculate_risk(**flags))
    else:
        result.update({
            "score": None,
            "level": None,
            "reasons": [],
        })

    return result
