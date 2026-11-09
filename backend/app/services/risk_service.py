
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
    coordinates: list[list[float]] | None = None,
    slope_percent: float | None = None,
    slope_threshold_percent: float | None = None,
    heavy_rain: bool | None = None,
    low_visibility: bool | None = None,
    heavy_traffic: bool | None = None,
    proximity_m: float = DEFAULT_PROXIMITY_M,
) -> dict[str, Any]:
    """Assess a segment without treating unknown inputs as safe.

    Spatial checks use the complete LineString when coordinates are supplied.

    Historical landslide data is considered unknown when unlocated landslide
    records exist and no nearby geocoded incident can be confirmed.
    """

    # Validate proximity.
    if proximity_m <= 0:
        raise ValueError("proximity_m must be greater than zero")

    # Validate endpoints.
    if len(start) != 2 or len(end) != 2:
        raise ValueError(
            "Segment endpoints must be [longitude, latitude]"
        )

    segment_coordinates = coordinates or [start, end]

    if len(segment_coordinates) < 2:
        raise ValueError(
            "Segment must contain at least two coordinates"
        )

    if any(len(point) != 2 for point in segment_coordinates):
        raise ValueError(
            "Segment coordinates must be [longitude, latitude] pairs"
        )

    # Build the complete route segment geometry.
    coordinate_text = ", ".join(
        f"{float(lon)} {float(lat)}"
        for lon, lat in segment_coordinates
    )

    segment_geom = func.ST_GeomFromText(
        f"LINESTRING({coordinate_text})",
        4326,
    )

    segment_geography = cast(
        segment_geom,
        Geography(srid=4326),
    )

    # Check for nearby geocoded historical landslide incidents.
    nearby_incident = db.scalar(
        select(IncidentHistory.id)
        .where(
            IncidentHistory.geom.is_not(None),
            func.lower(IncidentHistory.type).contains("landslide"),
            func.ST_DWithin(
                cast(
                    IncidentHistory.geom,
                    Geography(srid=4326),
                ),
                segment_geography,
                proximity_m,
            ),
        )
        .limit(1)
    )

    # Check whether any historical landslide records lack coordinates.
    unlocated_incident = db.scalar(
        select(IncidentHistory.id)
        .where(
            IncidentHistory.geom.is_(None),
            func.lower(IncidentHistory.type).contains("landslide"),
        )
        .limit(1)
    )

    if nearby_incident is not None:
        incident_nearby: bool | None = True
    elif unlocated_incident is not None:
        # We cannot safely conclude that no nearby historical incident exists.
        incident_nearby = None
    else:
        incident_nearby = False

    # Check for active nearby landslide or falling-rock reports.
    now = datetime.utcnow()

    hazard_nearby = db.scalar(
        select(Report.id)
        .where(
            Report.geom.is_not(None),
            Report.status == "active",
            Report.type.in_(["landslide", "falling_rock"]),
            or_(
                Report.expires_at.is_(None),
                Report.expires_at > now,
            ),
            func.ST_DWithin(
                cast(
                    Report.geom,
                    Geography(srid=4326),
                ),
                segment_geography,
                proximity_m,
            ),
        )
        .limit(1)
    ) is not None

    # Classify steep slope.
    steep_slope: bool | None = None

    if slope_percent is not None and slope_threshold_percent is not None:
        if slope_threshold_percent <= 0:
            raise ValueError(
                "slope_threshold_percent must be greater than zero"
            )

        steep_slope = (
            abs(slope_percent) >= slope_threshold_percent
        )

    # Keep the existing six-boolean risk contract.
    flags = {
        "heavy_rain": heavy_rain,
        "landslide_history": incident_nearby,
        "steep_slope": steep_slope,
        "recent_hazard_report": hazard_nearby,
        "heavy_traffic": heavy_traffic,
        "low_visibility": low_visibility,
    }

    # Unknown inputs must not be interpreted as safe.
    missing_inputs = [
        name
        for name, value in flags.items()
        if value is None
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
