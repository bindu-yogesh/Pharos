
from datetime import date, datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient
from geoalchemy2 import WKTElement
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.models import IncidentHistory, Report, ReportVote, User


def create_user(
    db_session: Session,
    email: str,
    role: str = "driver",
) -> User:
    user = User(
        name=f"Test {role.title()}",
        email=email,
        password_hash="test-password-hash",
        role=role,
        preferred_language="en",
        is_blocked=False,
    )
    db_session.add(user)
    db_session.flush()
    return user


def auth_headers(user: User) -> dict[str, str]:
    token = jwt.encode(
        {
            "sub": str(user.id),
            "role": user.role,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    return {"Authorization": f"Bearer {token}"}


def create_report(
    db_session: Session,
    user: User,
    *,
    status: str = "active",
    report_type: str = "landslide",
) -> Report:
    now = datetime.now(timezone.utc)
    report = Report(
        user_id=user.id,
        type=report_type,
        severity=2,
        description="Test hazard report",
        geom=WKTElement("POINT(77.5946 12.9716)", srid=4326),
        status=status,
        created_at=now,
        expires_at=now + timedelta(hours=24),
    )
    db_session.add(report)
    db_session.flush()
    return report


def create_incident(db_session: Session) -> IncidentHistory:
    incident = IncidentHistory(
        external_id="ADMIN-TEST-001",
        incident_date=date(2026, 10, 20),
        type="landslide",
        location_name="Test Road",
        geom=WKTElement("POINT(77.5946 12.9716)", srid=4326),
        location_confidence="exact",
        source="Test source",
        notes="Original notes",
    )
    db_session.add(incident)
    db_session.flush()
    return incident


@pytest.fixture
def admin_user(db_session: Session) -> User:
    return create_user(db_session, "admin-test@example.com", "admin")


@pytest.fixture
def driver_user(db_session: Session) -> User:
    return create_user(db_session, "driver-test@example.com", "driver")


ADMIN_ENDPOINTS = [
    ("PUT", "/admin/users/999999/block", {"is_blocked": True}),
    ("GET", "/admin/reports/suspicious", None),
    ("DELETE", "/admin/reports/999999", None),
    ("PUT", "/admin/incidents/999999", {"notes": "Updated"}),
    ("GET", "/admin/hazards", None),
    ("GET", "/admin/stats", None),
]


def send_request(
    client: TestClient,
    method: str,
    path: str,
    headers: dict | None = None,
    json: dict | None = None,
):
    return client.request(
        method,
        path,
        headers=headers,
        json=json,
    )


@pytest.mark.parametrize("method,path,payload", ADMIN_ENDPOINTS)
def test_admin_endpoints_require_authentication(
    client,
    method,
    path,
    payload,
):
    response = send_request(client, method, path, json=payload)
    assert response.status_code == 401


@pytest.mark.parametrize("method,path,payload", ADMIN_ENDPOINTS)
def test_driver_cannot_access_admin_endpoints(
    client,
    driver_user,
    method,
    path,
    payload,
):
    response = send_request(
        client,
        method,
        path,
        headers=auth_headers(driver_user),
        json=payload,
    )
    assert response.status_code == 403


def test_admin_can_block_and_unblock_user(
    client,
    db_session,
    admin_user,
):
    target = create_user(db_session, "block-target@example.com")
    db_session.commit()

    response = client.put(
        f"/admin/users/{target.id}/block",
        headers=auth_headers(admin_user),
        json={"is_blocked": True},
    )

    assert response.status_code == 200
    assert response.json()["is_blocked"] is True

    response = client.put(
        f"/admin/users/{target.id}/block",
        headers=auth_headers(admin_user),
        json={"is_blocked": False},
    )

    assert response.status_code == 200
    assert response.json()["is_blocked"] is False


def test_admin_cannot_block_self(client, admin_user):
    response = client.put(
        f"/admin/users/{admin_user.id}/block",
        headers=auth_headers(admin_user),
        json={"is_blocked": True},
    )

    assert response.status_code == 400


def test_block_user_returns_404_for_missing_user(
    client,
    admin_user,
):
    response = client.put(
        "/admin/users/999999/block",
        headers=auth_headers(admin_user),
        json={"is_blocked": True},
    )

    assert response.status_code == 404


def test_admin_can_reject_report(
    client,
    db_session,
    admin_user,
    driver_user,
):
    report = create_report(db_session, driver_user)
    db_session.commit()

    response = client.delete(
        f"/admin/reports/{report.id}",
        headers=auth_headers(admin_user),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "rejected"

    db_session.refresh(report)
    assert report.status == "rejected"


def test_reject_report_returns_404(
    client,
    admin_user,
):
    response = client.delete(
        "/admin/reports/999999",
        headers=auth_headers(admin_user),
    )

    assert response.status_code == 404


def test_admin_can_update_incident(
    client,
    db_session,
    admin_user,
):
    incident = create_incident(db_session)
    db_session.commit()

    response = client.put(
        f"/admin/incidents/{incident.id}",
        headers=auth_headers(admin_user),
        json={
            "type": "blockage",
            "incident_date": "2026-10-21",
            "location_name": "Updated Road",
            "latitude": 13.0,
            "longitude": 77.6,
            "source": "Updated source",
            "notes": "Updated notes",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "blockage"
    assert data["incident_date"] == "2026-10-21"
    assert data["location_name"] == "Updated Road"
    assert data["latitude"] == pytest.approx(13.0)
    assert data["longitude"] == pytest.approx(77.6)
    assert data["source"] == "Updated source"


def test_incident_update_rejects_only_one_coordinate(
    client,
    admin_user,
):
    response = client.put(
        "/admin/incidents/1",
        headers=auth_headers(admin_user),
        json={"latitude": 13.0},
    )

    assert response.status_code == 422


def test_update_incident_returns_404(
    client,
    admin_user,
):
    response = client.put(
        "/admin/incidents/999999",
        headers=auth_headers(admin_user),
        json={"notes": "Updated"},
    )

    assert response.status_code == 404


def test_admin_hazards_returns_active_hazards(
    client,
    db_session,
    admin_user,
    driver_user,
):
    report = create_report(db_session, driver_user)
    db_session.commit()

    response = client.get(
        "/admin/hazards",
        headers=auth_headers(admin_user),
    )

    assert response.status_code == 200
    hazard = next(
        item for item in response.json()
        if item["id"] == report.id
    )
    assert hazard["latitude"] == pytest.approx(12.9716)
    assert hazard["longitude"] == pytest.approx(77.5946)


def test_admin_stats_returns_required_fields(
    client,
    admin_user,
):
    response = client.get(
        "/admin/stats",
        headers=auth_headers(admin_user),
    )

    assert response.status_code == 200
    data = response.json()

    assert "total_users" in data
    assert "blocked_users" in data
    assert "total_reports" in data
    assert "active_reports" in data
    assert "active_hazards" in data
    assert "reports_by_type" in data
    assert "reports_by_status" in data
    assert "reports_by_day" in data

def test_admin_stats_excludes_reports_without_coordinates_from_active_hazards(
    client,
    db_session,
    admin_user,
):
    user = create_user(db_session, "no-coordinates@example.com")
    report = create_report(db_session, user, status="active")
    report.geom = None
    db_session.commit()

    response = client.get(
        "/admin/stats",
        headers=auth_headers(admin_user),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["active_reports"] == 1
    assert data["active_hazards"] == 0


# Additional Phase 5 behavior and edge-case tests


def test_suspicious_reports_flags_clear_vote_threshold(
    client,
    db_session,
    admin_user,
    driver_user,
):
    report = create_report(db_session, driver_user)

    voters = [
        create_user(db_session, f"threshold-voter-{i}@example.com")
        for i in range(settings.clear_votes_threshold)
    ]

    for voter in voters:
        db_session.add(
            ReportVote(
                report_id=report.id,
                user_id=voter.id,
                vote="clear",
            )
        )

    db_session.commit()

    response = client.get(
        "/admin/reports/suspicious",
        headers=auth_headers(admin_user),
    )

    assert response.status_code == 200
    flagged = [item for item in response.json() if item["id"] == report.id]
    assert len(flagged) == 1
    assert flagged[0]["clear_votes"] == settings.clear_votes_threshold


def test_suspicious_reports_includes_confirm_vote_counts(
    client,
    db_session,
    admin_user,
    driver_user,
):
    report = create_report(db_session, driver_user)

    clear_voters = [
        create_user(db_session, f"clear-voter-{i}@example.com")
        for i in range(settings.clear_votes_threshold)
    ]
    confirm_voter = create_user(db_session, "confirm-voter@example.com")

    for voter in clear_voters:
        db_session.add(
            ReportVote(
                report_id=report.id,
                user_id=voter.id,
                vote="clear",
            )
        )

    db_session.add(
        ReportVote(
            report_id=report.id,
            user_id=confirm_voter.id,
            vote="confirm",
        )
    )
    db_session.commit()

    response = client.get(
        "/admin/reports/suspicious",
        headers=auth_headers(admin_user),
    )

    assert response.status_code == 200
    flagged = next(item for item in response.json() if item["id"] == report.id)
    assert flagged["confirm_votes"] == 1
    assert flagged["clear_votes"] == settings.clear_votes_threshold


def test_suspicious_reports_flags_author_with_repeated_rejections(
    client,
    db_session,
    admin_user,
    driver_user,
):
    for _ in range(3):
        create_report(db_session, driver_user, status="rejected")

    db_session.commit()

    response = client.get(
        "/admin/reports/suspicious",
        headers=auth_headers(admin_user),
    )

    assert response.status_code == 200
    flagged_ids = {item["id"] for item in response.json()}
    rejected_reports = db_session.query(Report).filter_by(
        user_id=driver_user.id,
        status="rejected",
    ).all()

    assert len(rejected_reports) == 3
    assert all(report.id in flagged_ids for report in rejected_reports)


def test_hazards_excludes_cleared_reports(
    client,
    db_session,
    admin_user,
    driver_user,
):
    report = create_report(db_session, driver_user, status="cleared")
    db_session.commit()

    response = client.get(
        "/admin/hazards",
        headers=auth_headers(admin_user),
    )

    assert response.status_code == 200
    assert report.id not in {item["id"] for item in response.json()}


def test_hazards_excludes_expired_reports(
    client,
    db_session,
    admin_user,
    driver_user,
):
    report = create_report(db_session, driver_user)
    report.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    db_session.commit()

    response = client.get(
        "/admin/hazards",
        headers=auth_headers(admin_user),
    )

    assert response.status_code == 200
    assert report.id not in {item["id"] for item in response.json()}


def test_incident_update_preserves_unspecified_fields(
    client,
    db_session,
    admin_user,
):
    incident = create_incident(db_session)
    original_source = incident.source
    original_location = incident.location_name
    db_session.commit()

    response = client.put(
        f"/admin/incidents/{incident.id}",
        headers=auth_headers(admin_user),
        json={"notes": "Only notes changed"},
    )

    assert response.status_code == 200
    assert response.json()["notes"] == "Only notes changed"
    assert response.json()["source"] == original_source
    assert response.json()["location_name"] == original_location


def test_incident_update_rejects_out_of_range_coordinates(
    client,
    db_session,
    admin_user,
):
    incident = create_incident(db_session)
    db_session.commit()

    response = client.put(
        f"/admin/incidents/{incident.id}",
        headers=auth_headers(admin_user),
        json={
            "latitude": 120,
            "longitude": 77.6,
        },
    )

    assert response.status_code == 422


def test_stats_reflect_report_status_counts(
    client,
    db_session,
    admin_user,
    driver_user,
):
    create_report(db_session, driver_user, status="active")
    create_report(db_session, driver_user, status="cleared")
    create_report(db_session, driver_user, status="rejected")
    db_session.commit()

    response = client.get(
        "/admin/stats",
        headers=auth_headers(admin_user),
    )

    assert response.status_code == 200
    data = response.json()

    assert data["total_reports"] == 3
    assert data["reports_by_status"]["active"] == 1
    assert data["reports_by_status"]["cleared"] == 1
    assert data["reports_by_status"]["rejected"] == 1
    assert data["reports_by_type"]["landslide"] == 3


def test_blocked_admin_cannot_access_admin_endpoints(
    client,
    db_session,
    admin_user,
):
    admin_user.is_blocked = True
    db_session.commit()

    response = client.get(
        "/admin/stats",
        headers=auth_headers(admin_user),
    )

    assert response.status_code == 403


def test_admin_can_submit_self_unblock_request_without_being_blocked(
    client,
    admin_user,
):
    response = client.put(
        f"/admin/users/{admin_user.id}/block",
        headers=auth_headers(admin_user),
        json={"is_blocked": False},
    )

    assert response.status_code == 200
    assert response.json()["is_blocked"] is False
