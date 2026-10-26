def test_create_report_success(client):
    # Register a driver
    client.post(
        "/auth/register",
        json={
            "name": "Report Driver",
            "email": "report@example.com",
            "password": "TestPassword123!",
            "preferred_language": "en",
        },
    )

    # Log in and obtain the access token
    login_response = client.post(
        "/auth/login",
        json={
            "email": "report@example.com",
            "password": "TestPassword123!",
        },
    )

    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    # Create a hazard report
    response = client.post(
        "/reports",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "type": "landslide",
            "severity": 2,
            "description": "Landslide reported near the road",
            "latitude": 12.9716,
            "longitude": 77.5946,
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["type"] == "landslide"
    assert data["severity"] == 2
    assert data["latitude"] == 12.9716
    assert data["longitude"] == 77.5946
    assert data["status"] == "active"
    assert data["user_id"] > 0
    assert data["expires_at"] is not None

def test_create_report_requires_authentication(client):
    response = client.post(
        "/reports",
        json={
            "type": "landslide",
            "severity": 2,
            "description": "Landslide reported near the road",
            "latitude": 12.9716,
            "longitude": 77.5946,
        },
    )

    assert response.status_code == 401

def get_report_auth_headers(client, email):
    password = "TestPassword123!"

    register_response = client.post(
        "/auth/register",
        json={
            "name": "Validation Driver",
            "email": email,
            "password": password,
            "preferred_language": "en",
        },
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert login_response.status_code == 200

    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_create_report_rejects_invalid_type(client):
    headers = get_report_auth_headers(client, "invalid-type@example.com")

    response = client.post(
        "/reports",
        headers=headers,
        json={
            "type": "pothole",
            "severity": 2,
            "description": "Invalid report type",
            "latitude": 12.9716,
            "longitude": 77.5946,
        },
    )

    assert response.status_code == 422

def test_create_report_rejects_invalid_severity(client):
    headers = get_report_auth_headers(client, "invalid-severity@example.com")

    response = client.post(
        "/reports",
        headers=headers,
        json={
            "type": "landslide",
            "severity": 4,
            "description": "Invalid severity",
            "latitude": 12.9716,
            "longitude": 77.5946,
        },
    )

    assert response.status_code == 422

def test_create_report_rejects_invalid_coordinates(client):
    headers = get_report_auth_headers(client, "invalid-coordinates@example.com")

    response = client.post(
        "/reports",
        headers=headers,
        json={
            "type": "landslide",
            "severity": 2,
            "description": "Invalid latitude",
            "latitude": 91,
            "longitude": 77.5946,
        },
    )

    assert response.status_code == 422

def test_create_report_rejects_invalid_longitude(client):
    headers = get_report_auth_headers(
        client, "invalid-longitude@example.com"
    )

    response = client.post(
        "/reports",
        headers=headers,
        json={
            "type": "landslide",
            "severity": 2,
            "description": "Invalid longitude",
            "latitude": 12.9716,
            "longitude": 181,
        },
    )

    assert response.status_code == 422

def test_list_reports_returns_active_reports(client):
    headers = get_report_auth_headers(client, "list-active@example.com")

    create_response = client.post(
        "/reports",
        headers=headers,
        json={
            "type": "landslide",
            "severity": 2,
            "description": "Active landslide",
            "latitude": 12.9716,
            "longitude": 77.5946,
        },
    )
    assert create_response.status_code == 201

    response = client.get("/reports")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["type"] == "landslide"
    assert data[0]["confirm_votes"] == 0
    assert data[0]["clear_votes"] == 0


def test_list_reports_filters_by_type(client):
    headers = get_report_auth_headers(client, "list-type@example.com")

    for report_type in ("landslide", "blockage"):
        response = client.post(
            "/reports",
            headers=headers,
            json={
                "type": report_type,
                "severity": 2,
                "description": f"Test {report_type}",
                "latitude": 12.9716,
                "longitude": 77.5946,
            },
        )
        assert response.status_code == 201

    response = client.get("/reports", params={"type": "blockage"})

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["type"] == "blockage"

def test_list_reports_filters_by_bbox(client):
    headers = get_report_auth_headers(client, "list-bbox@example.com")

    for email_suffix, latitude, longitude in (
        ("inside", 12.9716, 77.5946),
        ("outside", 13.5, 78.0),
    ):
        response = client.post(
            "/reports",
            headers=headers,
            json={
                "type": "landslide",
                "severity": 2,
                "description": email_suffix,
                "latitude": latitude,
                "longitude": longitude,
            },
        )
        assert response.status_code == 201

    response = client.get(
        "/reports",
        params={"bbox": "77.4,12.8,77.7,13.1"},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["description"] == "inside"

def test_list_reports_rejects_invalid_bbox(client):
    response = client.get(
        "/reports",
        params={"bbox": "invalid,bbox"},
    )

    assert response.status_code == 422

def test_list_reports_rejects_invalid_type(client):
    response = client.get(
        "/reports",
        params={"type": "pothole"},
    )

    assert response.status_code == 422

def test_list_reports_enforces_pagination_limit(client):
    response = client.get("/reports", params={"limit": 501})

    assert response.status_code == 422

from datetime import datetime, timedelta, timezone

from sqlalchemy import update

from backend.app.models import Report

def test_list_reports_hides_expired_reports(client, db_session):
    headers = get_report_auth_headers(client, "expired-report@example.com")

    create_response = client.post(
        "/reports",
        headers=headers,
        json={
            "type": "landslide",
            "severity": 2,
            "description": "Expired report",
            "latitude": 12.9716,
            "longitude": 77.5946,
        },
    )
    assert create_response.status_code == 201

    report_id = create_response.json()["id"]
    expired_time = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1)

    db_session.execute(
        update(Report)
        .where(Report.id == report_id)
        .values(expires_at=expired_time)
    )
    db_session.flush()

    response = client.get("/reports")

    assert response.status_code == 200
    assert all(item["id"] != report_id for item in response.json())

def test_list_reports_filters_by_since(client):
    headers = get_report_auth_headers(client, "since-report@example.com")

    create_response = client.post(
        "/reports",
        headers=headers,
        json={
            "type": "blockage",
            "severity": 1,
            "description": "Recent blockage",
            "latitude": 12.9716,
            "longitude": 77.5946,
        },
    )
    assert create_response.status_code == 201

    response = client.get(
        "/reports",
        params={"since": "2099-01-01T00:00:00"},
    )

    assert response.status_code == 200
    assert all(
        item["id"] != create_response.json()["id"]
        for item in response.json()
    )

def test_list_reports_paginates(client):
    headers = get_report_auth_headers(client, "pagination-report@example.com")

    for index in range(3):
        response = client.post(
            "/reports",
            headers=headers,
            json={
                "type": "blockage",
                "severity": 1,
                "description": f"Pagination report {index}",
                "latitude": 12.9716,
                "longitude": 77.5946,
            },
        )
        assert response.status_code == 201

    first_page = client.get("/reports", params={"limit": 2, "offset": 0})
    second_page = client.get("/reports", params={"limit": 2, "offset": 2})

    assert first_page.status_code == 200
    assert second_page.status_code == 200
    assert len(first_page.json()) == 2
    assert len(second_page.json()) == 1

    first_ids = {item["id"] for item in first_page.json()}
    second_ids = {item["id"] for item in second_page.json()}
    assert first_ids.isdisjoint(second_ids)

def test_confirm_report_success(client):
    owner_headers = get_report_auth_headers(
        client, "confirm-owner@example.com"
    )
    voter_headers = get_report_auth_headers(
        client, "confirm-voter@example.com"
    )

    created = client.post(
        "/reports",
        headers=owner_headers,
        json={
            "type": "landslide",
            "severity": 2,
            "description": "Hazard to confirm",
            "latitude": 12.9716,
            "longitude": 77.5946,
        },
    )
    assert created.status_code == 201
    report_id = created.json()["id"]

    response = client.post(
        f"/reports/{report_id}/confirm",
        headers=voter_headers,
    )

    assert response.status_code == 200
    assert response.json()["vote"] == "confirm"

def test_clear_report_success(client):
    owner_headers = get_report_auth_headers(
        client, "clear-owner@example.com"
    )
    voter_headers = get_report_auth_headers(
        client, "clear-voter@example.com"
    )

    created = client.post(
        "/reports",
        headers=owner_headers,
        json={
            "type": "blockage",
            "severity": 1,
            "description": "Blockage to clear",
            "latitude": 12.9716,
            "longitude": 77.5946,
        },
    )
    assert created.status_code == 201

    response = client.post(
        f"/reports/{created.json()['id']}/clear",
        headers=voter_headers,
    )

    assert response.status_code == 200
    assert response.json()["vote"] == "clear"

def test_report_vote_rejects_own_report(client):
    owner_headers = get_report_auth_headers(
        client, "own-vote-owner@example.com"
    )

    created = client.post(
        "/reports",
        headers=owner_headers,
        json={
            "type": "landslide",
            "severity": 2,
            "description": "Owner cannot vote",
            "latitude": 12.9716,
            "longitude": 77.5946,
        },
    )
    assert created.status_code == 201

    response = client.post(
        f"/reports/{created.json()['id']}/confirm",
        headers=owner_headers,
    )

    assert response.status_code == 403

def test_report_vote_rejects_duplicate_vote(client):
    owner_headers = get_report_auth_headers(
        client, "duplicate-owner@example.com"
    )
    voter_headers = get_report_auth_headers(
        client, "duplicate-voter@example.com"
    )

    created = client.post(
        "/reports",
        headers=owner_headers,
        json={
            "type": "blockage",
            "severity": 1,
            "description": "Duplicate vote test",
            "latitude": 12.9716,
            "longitude": 77.5946,
        },
    )
    report_id = created.json()["id"]

    first = client.post(
        f"/reports/{report_id}/confirm",
        headers=voter_headers,
    )
    second = client.post(
        f"/reports/{report_id}/confirm",
        headers=voter_headers,
    )

    assert first.status_code == 200
    assert second.status_code == 409

def test_report_vote_returns_404_for_missing_report(client):
    voter_headers = get_report_auth_headers(
        client, "missing-report-voter@example.com"
    )

    response = client.post(
        "/reports/999999/confirm",
        headers=voter_headers,
    )

    assert response.status_code == 404

def test_report_vote_requires_authentication(client):
    response = client.post("/reports/1/confirm")

    assert response.status_code == 401

def test_expired_report_rejects_vote(client, db_session):
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import update
    from backend.app.models import Report

    owner_headers = get_report_auth_headers(
        client, "expired-vote-owner@example.com"
    )
    voter_headers = get_report_auth_headers(
        client, "expired-vote-voter@example.com"
    )

    created = client.post(
        "/reports",
        headers=owner_headers,
        json={
            "type": "landslide",
            "severity": 2,
            "description": "Expired hazard",
            "latitude": 12.9716,
            "longitude": 77.5946,
        },
    )
    report_id = created.json()["id"]

    expired_at = (
        datetime.now(timezone.utc).replace(tzinfo=None)
        - timedelta(hours=1)
    )
    db_session.execute(
        update(Report)
        .where(Report.id == report_id)
        .values(expires_at=expired_at)
    )
    db_session.flush()

    response = client.post(
        f"/reports/{report_id}/confirm",
        headers=voter_headers,
    )

    assert response.status_code == 400

def test_vote_rejects_report_with_no_expiry(client, db_session):
    from sqlalchemy import update
    from backend.app.models import Report

    owner_headers = get_report_auth_headers(
        client, "null-expiry-owner@example.com"
    )
    voter_headers = get_report_auth_headers(
        client, "null-expiry-voter@example.com"
    )

    created = client.post(
        "/reports",
        headers=owner_headers,
        json={
            "type": "landslide",
            "severity": 2,
            "description": "Report without expiry",
            "latitude": 12.9716,
            "longitude": 77.5946,
        },
    )
    assert created.status_code == 201
    report_id = created.json()["id"]

    db_session.execute(
        update(Report)
        .where(Report.id == report_id)
        .values(expires_at=None)
    )
    db_session.flush()

    response = client.post(
        f"/reports/{report_id}/confirm",
        headers=voter_headers,
    )

    assert response.status_code == 400

def test_inactive_report_rejects_vote(client, db_session):
    from sqlalchemy import update
    from backend.app.models import Report

    owner_headers = get_report_auth_headers(
        client, "inactive-report-owner@example.com"
    )
    voter_headers = get_report_auth_headers(
        client, "inactive-report-voter@example.com"
    )

    created = client.post(
        "/reports",
        headers=owner_headers,
        json={
            "type": "landslide",
            "severity": 2,
            "description": "Inactive report",
            "latitude": 12.9716,
            "longitude": 77.5946,
        },
    )
    assert created.status_code == 201
    report_id = created.json()["id"]

    db_session.execute(
        update(Report)
        .where(Report.id == report_id)
        .values(status="cleared")
    )
    db_session.flush()

    response = client.post(
        f"/reports/{report_id}/confirm",
        headers=voter_headers,
    )

    assert response.status_code == 400

def test_three_clear_votes_clear_report(client):
    owner_headers = get_report_auth_headers(
        client, "threshold-owner@example.com"
    )

    created = client.post(
        "/reports",
        headers=owner_headers,
        json={
            "type": "blockage",
            "severity": 1,
            "description": "Threshold test",
            "latitude": 12.9716,
            "longitude": 77.5946,
        },
    )
    assert created.status_code == 201
    report_id = created.json()["id"]

    for index in range(3):
        voter_headers = get_report_auth_headers(
            client, f"threshold-voter-{index}@example.com"
        )
        response = client.post(
            f"/reports/{report_id}/clear",
            headers=voter_headers,
        )
        assert response.status_code == 200

    response = client.get(
        "/reports",
        params={"type": "blockage"},
    )

    assert response.status_code == 200
    assert all(item["id"] != report_id for item in response.json())

def test_confirm_vote_extends_report_expiry(client):
    from datetime import datetime

    owner_headers = get_report_auth_headers(
        client, "expiry-extension-owner@example.com"
    )
    voter_headers = get_report_auth_headers(
        client, "expiry-extension-voter@example.com"
    )

    created = client.post(
        "/reports",
        headers=owner_headers,
        json={
            "type": "landslide",
            "severity": 2,
            "description": "Expiry extension test",
            "latitude": 12.9716,
            "longitude": 77.5946,
        },
    )
    assert created.status_code == 201
    report_id = created.json()["id"]
    original_expiry = datetime.fromisoformat(
        created.json()["expires_at"]
    )

    response = client.post(
        f"/reports/{report_id}/confirm",
        headers=voter_headers,
    )
    assert response.status_code == 200

    listed = client.get("/reports")
    report = next(
        item for item in listed.json() if item["id"] == report_id
    )
    extended_expiry = datetime.fromisoformat(report["expires_at"])

    assert extended_expiry > original_expiry

def test_create_report_rate_limit(client, monkeypatch):
    from backend.app.core.config import settings

    monkeypatch.setattr(settings, "reports_per_hour_limit", 2)

    headers = get_report_auth_headers(
        client, "rate-limit-driver@example.com"
    )

    payload = {
        "type": "landslide",
        "severity": 2,
        "description": "Rate limit test",
        "latitude": 12.9716,
        "longitude": 77.5946,
    }

    first = client.post("/reports", headers=headers, json=payload)
    second = client.post("/reports", headers=headers, json=payload)
    third = client.post("/reports", headers=headers, json=payload)

    assert first.status_code == 201
    assert second.status_code == 201
    assert third.status_code == 429

from backend.app.routers.reports import is_suspicious_report

def test_report_suspicious_when_clear_vote_threshold_reached(
    client, db_session
):
    from backend.app.core.config import settings
    from backend.app.models import Report, ReportVote, User
    from backend.app.routers.reports import is_suspicious_report

    author_headers = get_report_auth_headers(
        client, "suspicious-author@example.com"
    )

    response = client.post(
        "/reports",
        headers=author_headers,
        json={
            "type": "landslide",
            "severity": 2,
            "description": "Suspicious report test",
            "latitude": 12.9716,
            "longitude": 77.5946,
        },
    )
    assert response.status_code == 201

    report = db_session.get(Report, response.json()["id"])
    assert report is not None

    # Create real users so the vote foreign keys remain valid.
    voter_ids = []
    for index in range(settings.clear_votes_threshold):
        email = f"suspicious-voter-{index}@example.com"
        get_report_auth_headers(client, email)

        voter = db_session.query(User).filter_by(email=email).one()
        voter_ids.append(voter.id)

    for voter_id in voter_ids:
        db_session.add(
            ReportVote(
                report_id=report.id,
                user_id=voter_id,
                vote="clear",
            )
        )

    db_session.flush()

    assert is_suspicious_report(db_session, report) is True

def test_normal_report_is_not_suspicious(client, db_session):
    from backend.app.models import Report
    from backend.app.routers.reports import is_suspicious_report

    headers = get_report_auth_headers(
        client, "normal-report-author@example.com"
    )

    response = client.post(
        "/reports",
        headers=headers,
        json={
            "type": "landslide",
            "severity": 1,
            "description": "Normal report",
            "latitude": 12.9716,
            "longitude": 77.5946,
        },
    )

    assert response.status_code == 201

    report = db_session.get(Report, response.json()["id"])
    assert report is not None

    assert is_suspicious_report(db_session, report) is False

def test_author_with_repeated_rejected_reports_is_suspicious(
    client, db_session
):
    from backend.app.models import Report, User
    from backend.app.routers.reports import is_suspicious_report

    email = "rejected-author@example.com"
    headers = get_report_auth_headers(client, email)

    payload = {
        "type": "landslide",
        "severity": 2,
        "description": "Rejected report test",
        "latitude": 12.9716,
        "longitude": 77.5946,
    }

    report_ids = []
    for _ in range(3):
        response = client.post(
            "/reports", headers=headers, json=payload
        )
        assert response.status_code == 201
        report_ids.append(response.json()["id"])

    author = db_session.query(User).filter_by(email=email).one()

    for report_id in report_ids:
        report = db_session.get(Report, report_id)
        report.status = "rejected"

    db_session.flush()

    report = db_session.get(Report, report_ids[0])
    assert report.user_id == author.id
    assert is_suspicious_report(db_session, report) is True

def test_report_with_no_clear_votes_is_not_suspicious(
    client, db_session
):
    from backend.app.models import Report
    from backend.app.routers.reports import is_suspicious_report

    headers = get_report_auth_headers(
        client, "no-clear-votes@example.com"
    )
    response = client.post(
        "/reports",
        headers=headers,
        json={
            "type": "blockage",
            "severity": 1,
            "description": "No suspicious votes",
            "latitude": 12.9716,
            "longitude": 77.5946,
        },
    )

    assert response.status_code == 201
    report = db_session.get(Report, response.json()["id"])

    assert is_suspicious_report(db_session, report) is False

def test_create_report_rejects_invalid_severity(client):
    headers = get_report_auth_headers(
        client, "invalid-severity@example.com"
    )
    response = client.post(
        "/reports",
        headers=headers,
        json={
            "type": "landslide",
            "severity": 4,
            "description": "Invalid severity",
            "latitude": 12.9716,
            "longitude": 77.5946,
        },
    )

    assert response.status_code == 422

def test_create_report_rejects_invalid_report_type(client):
    headers = get_report_auth_headers(
        client, "invalid-type@example.com"
    )
    response = client.post(
        "/reports",
        headers=headers,
        json={
            "type": "invalid_type",
            "severity": 2,
            "description": "Invalid type",
            "latitude": 12.9716,
            "longitude": 77.5946,
        },
    )

    assert response.status_code == 422

def test_create_report_without_photo_url(client):
    headers = get_report_auth_headers(
        client, "no-photo@example.com"
    )

    response = client.post(
        "/reports",
        headers=headers,
        json={
            "type": "blockage",
            "severity": 2,
            "description": "Report without photo",
            "latitude": 12.9716,
            "longitude": 77.5946,
        },
    )

    assert response.status_code == 201
    assert response.json()["photo_url"] is None

def test_create_report_with_photo_url(client):
    headers = get_report_auth_headers(
        client, "photo-url@example.com"
    )
    photo_url = "https://example.com/road-damage.jpg"

    response = client.post(
        "/reports",
        headers=headers,
        json={
            "type": "blockage",
            "severity": 2,
            "description": "Road damage with photo",
            "latitude": 12.9716,
            "longitude": 77.5946,
            "photo_url": photo_url,
        },
    )

    assert response.status_code == 201
    assert response.json()["photo_url"] == photo_url

def test_create_report_rejects_latitude_out_of_range(client):
    headers = get_report_auth_headers(
        client, "invalid-latitude@example.com"
    )

    response = client.post(
        "/reports",
        headers=headers,
        json={
            "type": "landslide",
            "severity": 2,
            "description": "Invalid latitude",
            "latitude": 91,
            "longitude": 77.5946,
        },
    )

    assert response.status_code == 422

def test_create_report_rejects_longitude_out_of_range(client):
    headers = get_report_auth_headers(
        client, "invalid-longitude@example.com"
    )

    response = client.post(
        "/reports",
        headers=headers,
        json={
            "type": "landslide",
            "severity": 2,
            "description": "Invalid longitude",
            "latitude": 12.9716,
            "longitude": 181,
        },
    )

    assert response.status_code == 422

def test_create_report_rejects_description_over_500_chars(client):
    headers = get_report_auth_headers(
        client, "long-description@example.com"
    )

    response = client.post(
        "/reports",
        headers=headers,
        json={
            "type": "landslide",
            "severity": 2,
            "description": "x" * 501,
            "latitude": 12.9716,
            "longitude": 77.5946,
        },
    )

    assert response.status_code == 422

def test_report_list_respects_limit_and_offset(client):
    headers = get_report_auth_headers(
        client, "pagination@example.com"
    )

    for index in range(3):
        response = client.post(
            "/reports",
            headers=headers,
            json={
                "type": "blockage",
                "severity": 1,
                "description": f"Pagination report {index}",
                "latitude": 12.9716,
                "longitude": 77.5946,
            },
        )
        assert response.status_code == 201

    response = client.get("/reports?limit=1&offset=1")

    assert response.status_code == 200
    assert len(response.json()) == 1

def test_report_list_filters_by_type(client):
    headers = get_report_auth_headers(
        client, "type-filter@example.com"
    )

    for report_type in ("landslide", "blockage"):
        response = client.post(
            "/reports",
            headers=headers,
            json={
                "type": report_type,
                "severity": 2,
                "description": f"Filter test {report_type}",
                "latitude": 12.9716,
                "longitude": 77.5946,
            },
        )
        assert response.status_code == 201

    response = client.get("/reports?type=landslide")

    assert response.status_code == 200
    assert all(
        item["type"] == "landslide"
        for item in response.json()
    )

def test_suspicious_helper_flags_repeated_rejections(
    client, db_session
):
    from backend.app.models import Report, User
    from backend.app.routers.reports import is_suspicious_report

    email = "repeated-rejections@example.com"
    headers = get_report_auth_headers(client, email)

    report_ids = []

    for index in range(3):
        response = client.post(
            "/reports",
            headers=headers,
            json={
                "type": "landslide",
                "severity": 2,
                "description": f"Rejected report {index}",
                "latitude": 12.9716,
                "longitude": 77.5946,
            },
        )
        assert response.status_code == 201
        report_ids.append(response.json()["id"])

    author = db_session.query(User).filter_by(email=email).one()

    for report_id in report_ids:
        report = db_session.get(Report, report_id)
        report.status = "rejected"

    db_session.flush()

    report = db_session.get(Report, report_ids[0])
    assert report.user_id == author.id
    assert is_suspicious_report(db_session, report) is True
