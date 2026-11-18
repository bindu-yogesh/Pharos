from datetime import datetime, timedelta

from unittest.mock import patch

from geoalchemy2 import WKTElement
from sqlalchemy import func, select

from backend.app.models.device import DeviceToken
from backend.app.models.report import Report
from backend.app.models.notification_outbox import NotificationOutbox
from backend.app.models.trip import Trip
from backend.app.models.user import User
from backend.app.services.trip_alert_service import (
    check_trip_hazards,
    deliver_pending_notifications,
)


def get_auth_headers(client, email):
    password = "TestPassword123!"

    registration = client.post(
        "/auth/register",
        json={
            "name": "Phase 6 Test Driver",
            "email": email,
            "password": password,
            "preferred_language": "en",
        },
    )
    assert registration.status_code == 201

    login = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200

    return {
        "Authorization": f"Bearer {login.json()['access_token']}"
    }


def get_user(db_session, email):
    return db_session.scalar(
        select(User).where(User.email == email)
    )


def create_trip(db_session, user_id):
    trip = Trip(
        user_id=user_id,
        route_json={"distance_m": 1000},
        status="active",
        last_latitude=12.0,
        last_longitude=75.0,
    )
    db_session.add(trip)
    db_session.flush()
    return trip


def create_report(db_session, user_id, report_type="landslide",
                  severity=2, longitude=75.0, latitude=12.0,
                  report_status="active"):
    report = Report(
        user_id=user_id,
        type=report_type,
        severity=severity,
        description="Test hazard",
        status=report_status,
        geom=WKTElement(
            f"POINT({longitude} {latitude})",
            srid=4326,
        ),
    )
    db_session.add(report)
    db_session.flush()
    return report


def test_device_registration_requires_authentication(client):
    response = client.post(
        "/devices",
        json={"fcm_token": "test-device-token"},
    )
    assert response.status_code == 401


def test_device_registration_and_token_upsert(client, db_session):
    owner_headers = get_auth_headers(
        client, "device-owner@example.com"
    )
    other_headers = get_auth_headers(
        client, "device-other@example.com"
    )

    payload = {"fcm_token": "phase6-test-fcm-token"}

    first = client.post(
        "/devices", headers=owner_headers, json=payload
    )
    assert first.status_code == 200

    second = client.post(
        "/devices", headers=owner_headers, json=payload
    )
    assert second.status_code == 200

    token_count = db_session.scalar(
        select(func.count())
        .select_from(DeviceToken)
        .where(DeviceToken.fcm_token == payload["fcm_token"])
    )
    assert token_count == 1

    # Registering the same token under another account transfers ownership.
    transferred = client.post(
        "/devices", headers=other_headers, json=payload
    )
    assert transferred.status_code == 200

    token = db_session.scalar(
        select(DeviceToken).where(
            DeviceToken.fcm_token == payload["fcm_token"]
        )
    )
    other_user = get_user(
        db_session, "device-other@example.com"
    )

    assert token.user_id == other_user.id


def test_trip_location_update_saves_coordinates(client, db_session):
    headers = get_auth_headers(
        client, "location-driver@example.com"
    )

    start = client.post(
        "/trips/start",
        headers=headers,
        json={"route_json": {"distance_m": 1000}},
    )
    assert start.status_code == 201

    trip_id = start.json()["id"]

    with patch(
        "backend.app.routers.trips.check_trip_hazards",
        return_value=0,
    ):
        response = client.post(
            f"/trips/{trip_id}/location",
            headers=headers,
            json={"latitude": 12.5, "longitude": 75.5},
        )

    assert response.status_code == 200
    assert response.json()["trip_id"] == trip_id
    assert response.json()["alerts_sent"] == 0

    trip = db_session.get(Trip, trip_id)
    assert trip.last_latitude == 12.5
    assert trip.last_longitude == 75.5
    assert trip.last_location_at is not None


def test_trip_location_update_rejects_wrong_owner(client):
    owner = get_auth_headers(
        client, "location-owner@example.com"
    )
    other = get_auth_headers(
        client, "location-other@example.com"
    )

    start = client.post(
        "/trips/start",
        headers=owner,
        json={"route_json": {"distance_m": 1000}},
    )
    trip_id = start.json()["id"]

    response = client.post(
        f"/trips/{trip_id}/location",
        headers=other,
        json={"latitude": 12.5, "longitude": 75.5},
    )

    assert response.status_code == 404


def test_ended_trip_rejects_location_update(client):
    headers = get_auth_headers(
        client, "ended-location@example.com"
    )

    start = client.post(
        "/trips/start",
        headers=headers,
        json={"route_json": {"distance_m": 1000}},
    )
    trip_id = start.json()["id"]

    ended = client.post(
        f"/trips/{trip_id}/end",
        headers=headers,
        json={"status": "ended"},
    )
    assert ended.status_code == 200

    response = client.post(
        f"/trips/{trip_id}/location",
        headers=headers,
        json={"latitude": 12.5, "longitude": 75.5},
    )

    assert response.status_code == 409


def test_location_update_rejects_invalid_coordinates(client):
    headers = get_auth_headers(
        client, "invalid-location@example.com"
    )

    start = client.post(
        "/trips/start",
        headers=headers,
        json={"route_json": {"distance_m": 1000}},
    )
    trip_id = start.json()["id"]

    response = client.post(
        f"/trips/{trip_id}/location",
        headers=headers,
        json={"latitude": 91, "longitude": 75},
    )

    assert response.status_code == 422


def test_nearby_hazard_sends_alert_to_all_devices(db_session, client):
    get_auth_headers(client, "hazard-driver@example.com")
    user = get_user(db_session, "hazard-driver@example.com")
    trip = create_trip(db_session, user.id)
    report = create_report(db_session, user.id)

    db_session.add_all([
        DeviceToken(user_id=user.id, fcm_token="hazard-device-one"),
        DeviceToken(user_id=user.id, fcm_token="hazard-device-two"),
    ])
    db_session.flush()

    result = check_trip_hazards(db_session, trip)

    assert result == 1
    assert report.id in trip.alerted_report_ids

    queued = db_session.scalars(
        select(NotificationOutbox).where(
            NotificationOutbox.trip_id == trip.id
        )
    ).all()
    assert len(queued) == 2
    assert all(item.status == "pending" for item in queued)

    with patch(
        "backend.app.integrations.fcm.send",
        return_value=True,
    ) as mock_send:
        delivered = deliver_pending_notifications(db_session)

    assert delivered == 2
    assert mock_send.call_count == 2


def test_hazard_alert_is_not_sent_twice(db_session, client):
    get_auth_headers(client, "dedup-driver@example.com")
    user = get_user(db_session, "dedup-driver@example.com")
    trip = create_trip(db_session, user.id)
    report = create_report(db_session, user.id)

    db_session.add(
        DeviceToken(user_id=user.id, fcm_token="dedup-device")
    )
    db_session.flush()

    first = check_trip_hazards(db_session, trip)
    second = check_trip_hazards(db_session, trip)

    assert first == 1
    assert second == 0
    assert report.id in trip.alerted_report_ids

    queued = db_session.scalars(
        select(NotificationOutbox).where(
            NotificationOutbox.trip_id == trip.id
        )
    ).all()
    assert len(queued) == 1

    with patch(
        "backend.app.integrations.fcm.send",
        return_value=True,
    ) as mock_send:
        delivered = deliver_pending_notifications(db_session)

    assert delivered == 1
    mock_send.assert_called_once()


def test_failed_hazard_delivery_can_be_retried(db_session, client):
    get_auth_headers(client, "retry-driver@example.com")
    user = get_user(db_session, "retry-driver@example.com")
    trip = create_trip(db_session, user.id)
    report = create_report(db_session, user.id)

    db_session.add(
        DeviceToken(user_id=user.id, fcm_token="retry-device")
    )
    db_session.flush()

    first = check_trip_hazards(db_session, trip)
    second = check_trip_hazards(db_session, trip)

    assert first == 1
    assert second == 0
    assert report.id in trip.alerted_report_ids

    with patch(
        "backend.app.integrations.fcm.send",
        side_effect=[False, True],
    ) as mock_send:
        first_delivery = deliver_pending_notifications(db_session)

        item = db_session.scalar(
            select(NotificationOutbox).where(
                NotificationOutbox.trip_id == trip.id
            )
        )
        assert item.status == "pending"
        assert item.attempts == 1

        item.next_attempt_at = datetime.utcnow() - timedelta(seconds=1)
        db_session.flush()

        second_delivery = deliver_pending_notifications(db_session)

    assert first_delivery == 0
    assert second_delivery == 1
    assert item.status == "sent"
    assert item.attempts == 1
    assert mock_send.call_count == 2


def test_low_severity_hazard_does_not_trigger_alert(db_session, client):
    get_auth_headers(
        client, "severity-driver@example.com"
    )
    user = get_user(db_session, "severity-driver@example.com")

    trip = create_trip(db_session, user.id)
    create_report(db_session, user.id, severity=1)

    db_session.add(
        DeviceToken(
            user_id=user.id,
            fcm_token="severity-device",
        )
    )
    db_session.flush()

    with patch(
        "backend.app.services.trip_alert_service.send"
    ) as mock_send:
        result = check_trip_hazards(db_session, trip)

    assert result == 0
    mock_send.assert_not_called()


def test_upcoming_route_segments_validate_finite_coordinates(db_session, client):
    get_auth_headers(
        client, "route-segment-driver@example.com"
    )
    user = get_user(
        db_session, "route-segment-driver@example.com"
    )
    trip = create_trip(db_session, user.id)

    result = check_trip_hazards(
        db_session,
        trip,
        upcoming_segments=[
            {
                "coordinates": [
                    [75.0, 12.0],
                    [75.01, 12.01],
                ]
            }
        ],
    )

    assert result == 0
