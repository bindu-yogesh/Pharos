from datetime import datetime, timedelta

from unittest.mock import patch

from sqlalchemy import select
from backend.app.models.notification_outbox import NotificationOutbox

from backend.app.models.device import DeviceToken
from backend.app.models.trip import Trip
from backend.app.models.user import User
from backend.app.services.trip_alert_service import (
    check_trip_risk_escalation,
    deliver_pending_notifications,
)


def create_test_trip(db_session, email):
    user = User(
        name="Risk Test Driver",
        email=email,
        password_hash="test-password-hash",
    )
    db_session.add(user)
    db_session.flush()

    trip = Trip(
        user_id=user.id,
        route_json={"distance_m": 1000},
        status="active",
    )
    db_session.add(trip)

    db_session.add(
        DeviceToken(
            user_id=user.id,
            fcm_token=f"token-{email}",
        )
    )

    db_session.flush()
    return trip


def test_escalation_sends_notification(db_session):
    trip = create_test_trip(db_session, "escalation@example.com")
    trip.last_alerted_level = "Green"

    result = check_trip_risk_escalation(db_session, trip, "Yellow")

    assert result is True
    assert trip.last_alerted_level == "Yellow"

    queued = db_session.scalars(
        select(NotificationOutbox).where(
            NotificationOutbox.trip_id == trip.id
        )
    ).all()
    assert len(queued) == 1
    assert queued[0].status == "pending"

    with patch(
        "backend.app.integrations.fcm.send",
        return_value=True,
    ) as mock_send:
        delivered = deliver_pending_notifications(db_session)

    assert delivered == 1
    mock_send.assert_called_once()


def test_same_level_does_not_send_notification(db_session):
    trip = create_test_trip(
        db_session, "same-level@example.com"
    )
    trip.last_alerted_level = "Yellow"

    with patch(
        "backend.app.integrations.fcm.send"
    ) as mock_send:
        result = check_trip_risk_escalation(
            db_session, trip, "Yellow"
        )

    assert result is False
    mock_send.assert_not_called()


def test_failed_notification_can_be_retried(db_session):
    trip = create_test_trip(db_session, "retry-risk@example.com")
    trip.last_alerted_level = "Green"

    first = check_trip_risk_escalation(db_session, trip, "Orange")
    second = check_trip_risk_escalation(db_session, trip, "Orange")

    assert first is True
    assert second is False
    assert trip.last_alerted_level == "Orange"

    item = db_session.scalar(
        select(NotificationOutbox).where(
            NotificationOutbox.trip_id == trip.id
        )
    )
    assert item is not None
    assert item.status == "pending"

    with patch(
        "backend.app.integrations.fcm.send",
        side_effect=[False, True],
    ) as mock_send:
        first_delivery = deliver_pending_notifications(db_session)

        assert item.attempts == 1
        assert item.status == "pending"

        item.next_attempt_at = datetime.utcnow() - timedelta(seconds=1)
        db_session.flush()

        second_delivery = deliver_pending_notifications(db_session)

    assert first_delivery == 0
    assert second_delivery == 1
    assert item.status == "sent"
    assert item.attempts == 1
    assert mock_send.call_count == 2


def test_incomplete_assessment_does_not_notify(db_session):
    trip = create_test_trip(
        db_session, "incomplete-risk@example.com"
    )

    with patch(
        "backend.app.integrations.fcm.send"
    ) as mock_send:
        result = check_trip_risk_escalation(
            db_session, trip, None
        )

    assert result is False
    mock_send.assert_not_called()


def test_risk_downgrade_updates_baseline_without_alert(db_session):
    trip = create_test_trip(
        db_session, "downgrade-risk@example.com"
    )
    trip.last_alerted_level = "Orange"

    with patch(
        "backend.app.integrations.fcm.send"
    ) as mock_send:
        result = check_trip_risk_escalation(
            db_session, trip, "Yellow"
        )

    assert result is False
    assert trip.last_alerted_level == "Yellow"
    mock_send.assert_not_called()
