from backend.app.models.user import User
from datetime import date, datetime, timedelta
from backend.app.models.segment import RoadSegment
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.models.incident import IncidentHistory
from backend.app.models.report import Report
from backend.app.services.risk_service import assess_segment_risk


def add_incident(db: Session, longitude: float, latitude: float) -> None:
    incident = IncidentHistory(
        external_id=f"risk-test-{datetime.utcnow().timestamp()}",
        incident_date=date.today(),
        type="landslide",
        location_name="Risk service integration test",
        geom=None,
        location_confidence="exact",
        source="automated test",
    )
    db.add(incident)
    db.flush()
    db.execute(
        text("""
            UPDATE incidents_history
            SET geom = ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)
            WHERE id = :id
        """),
        {"lon": longitude, "lat": latitude, "id": incident.id},
    )


def add_report(
    db: Session,
    longitude: float,
    latitude: float,
    *,
    status: str = "active",
    expires_at: datetime | None = None,
):
    user = User(
        name="Risk Service Test User",
        email=f"risk-test-{datetime.utcnow().timestamp()}@example.com",
        password_hash="test-only-password-hash",
    )
    db.add(user)
    db.flush()

    report = Report(
        user_id=user.id,
        type="landslide",
        severity=2,
        description="Risk service integration test",
        status=status,
        created_at=datetime.utcnow(),
        expires_at=expires_at,
        geom=None,
    )
    db.add(report)
    db.flush()

    db.execute(
        text(
            """
            UPDATE reports
            SET geom = ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)
            WHERE id = :id
            """
        ),
        {"lon": longitude, "lat": latitude, "id": report.id},
    )

    return report


def assess(db: Session):
    return assess_segment_risk(
        db,
        start=[75.0, 12.0],
        end=[75.01, 12.0],
        slope_percent=2.0,
        slope_threshold_percent=6.0,
        heavy_rain=False,
        low_visibility=False,
        heavy_traffic=False,
    )


def test_nearby_historical_landslide_is_detected(db_session):
    add_incident(db_session, 75.005, 12.001)

    result = assess(db_session)

    assert result["risk_flags"]["landslide_history"] is True


def test_nearby_active_report_is_detected(db_session):
    add_report(db_session, 75.005, 12.001)

    result = assess(db_session)

    assert result["risk_flags"]["recent_hazard_report"] is True


def test_expired_report_is_ignored(db_session):
    add_report(
        db_session,
        75.005,
        12.001,
        expires_at=datetime.utcnow() - timedelta(hours=1),
    )

    result = assess(db_session)

    assert result["risk_flags"]["recent_hazard_report"] is False


def test_distant_active_report_is_ignored(db_session):
    add_report(db_session, 76.0, 13.0)

    result = assess(db_session)

    assert result["risk_flags"]["recent_hazard_report"] is False

def test_road_segment_model_accepts_test_geometry(db_session):
    segment = RoadSegment(
        segment_no=987654,
        geom="SRID=4326;LINESTRING(75.0 12.0, 75.01 12.0)",
        length_m=1000.0,
        elevation_start_m=100.0,
        elevation_end_m=102.0,
        slope_percent=0.2,
    )
    db_session.add(segment)
    db_session.flush()

    assert segment.id is not None
