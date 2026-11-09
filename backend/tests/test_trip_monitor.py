
import asyncio
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

from backend.app.services import trip_monitor


def make_trip(
    latitude=0.0,
    longitude=0.015,
    route_json=None,
):
    if route_json is None:
        route_json = {
            "distance_m": 2000,
            "duration_s": 2000,
            "segments": [
                {
                    "segment_id": 1,
                    "start": [0.0, 0.0],
                    "end": [0.01, 0.0],
                    "coordinates": [[0.0, 0.0], [0.01, 0.0]],
                    "length_m": 1000,
                },
                {
                    "segment_id": 2,
                    "start": [0.01, 0.0],
                    "end": [0.02, 0.0],
                    "coordinates": [[0.01, 0.0], [0.02, 0.0]],
                    "length_m": 1000,
                },
            ],
        }

    return SimpleNamespace(
        id=1,
        user_id=10,
        last_latitude=latitude,
        last_longitude=longitude,
        route_json=route_json,
        last_alerted_level=None,
    )


# Scheduler lifecycle tests

def test_start_trip_monitor():
    with patch.object(
        type(trip_monitor.scheduler),
        "running",
        new_callable=PropertyMock,
        return_value=False,
    ), patch.object(trip_monitor.scheduler, "add_job") as add_job, \
       patch.object(trip_monitor.scheduler, "start") as start:

        trip_monitor.start_trip_monitor()

        add_job.assert_called_once()
        start.assert_called_once()


def test_start_does_not_start_running_scheduler():
    with patch.object(
        type(trip_monitor.scheduler),
        "running",
        new_callable=PropertyMock,
        return_value=True,
    ), patch.object(trip_monitor.scheduler, "add_job") as add_job, \
       patch.object(trip_monitor.scheduler, "start") as start:

        trip_monitor.start_trip_monitor()

        add_job.assert_not_called()
        start.assert_not_called()


def test_stop_trip_monitor():
    with patch.object(
        type(trip_monitor.scheduler),
        "running",
        new_callable=PropertyMock,
        return_value=True,
    ), patch.object(trip_monitor.scheduler, "shutdown") as shutdown:

        trip_monitor.stop_trip_monitor()

        shutdown.assert_called_once_with(wait=False)


def test_stop_does_nothing_when_not_running():
    with patch.object(
        type(trip_monitor.scheduler),
        "running",
        new_callable=PropertyMock,
        return_value=False,
    ), patch.object(trip_monitor.scheduler, "shutdown") as shutdown:

        trip_monitor.stop_trip_monitor()

        shutdown.assert_not_called()


# Existing trip-monitoring tests

def test_monitor_active_trips_checks_recent_trips():
    mock_db = MagicMock()
    mock_db.scalars.return_value.all.return_value = [1]

    mock_trip = MagicMock()
    mock_trip.last_location_at = datetime.utcnow()
    mock_db.scalar.return_value = mock_trip

    with patch.object(trip_monitor, "SessionLocal", return_value=mock_db), \
         patch.object(
             trip_monitor, "check_trip_hazards", return_value=1
         ) as check, \
         patch.object(
             trip_monitor, "_assess_upcoming_route"
         ) as assess:

        trip_monitor.monitor_active_trips()

        check.assert_called_once_with(mock_db, mock_trip)
        assess.assert_called_once_with(mock_db, mock_trip)
        mock_db.commit.assert_called_once()
        mock_db.close.assert_called_once()


def test_monitor_skips_stale_trip():
    mock_db = MagicMock()
    mock_db.scalars.return_value.all.return_value = [1]

    mock_trip = MagicMock()
    mock_trip.last_location_at = datetime.utcnow() - timedelta(minutes=20)
    mock_db.scalar.return_value = mock_trip

    with patch.object(trip_monitor, "SessionLocal", return_value=mock_db), \
         patch.object(
             trip_monitor, "check_trip_hazards"
         ) as check, \
         patch.object(
             trip_monitor, "_assess_upcoming_route"
         ) as assess:

        trip_monitor.monitor_active_trips()

        check.assert_not_called()
        assess.assert_not_called()
        mock_db.close.assert_called_once()


# Route progress tests

def test_get_upcoming_segments_selects_nearest_segment():
    trip = make_trip()

    result = trip_monitor._get_upcoming_segments(trip)

    assert result is not None

    segments, average_speed = result

    assert [segment["segment_id"] for segment in segments] == [2]
    assert average_speed == 1.0


def test_get_upcoming_segments_rejects_trip_far_from_route():
    trip = make_trip(latitude=10.0, longitude=10.0)

    result = trip_monitor._get_upcoming_segments(trip)

    assert result is None


def test_get_upcoming_segments_rejects_ambiguous_routes():
    trip = make_trip(
        route_json={
            "routes": [
                {"segments": []},
                {"segments": []},
            ]
        }
    )

    result = trip_monitor._get_upcoming_segments(trip)

    assert result is None


def test_get_upcoming_segments_rejects_invalid_route():
    trip = make_trip(route_json={"distance_m": 1000})

    result = trip_monitor._get_upcoming_segments(trip)

    assert result is None


# Weather forecast tests

def test_fetch_weather_for_segments():
    segments = [
        {
            "segment_id": 1,
            "length_m": 1000,
            "coordinates": [[75.0, 12.0], [75.01, 12.01]],
        }
    ]

    forecast = {
        "precipitation_mm": 20,
        "visibility_m": 500,
    }

    with patch.object(
        trip_monitor,
        "get_weather_forecast",
        new_callable=AsyncMock,
        return_value=forecast,
    ) as weather:

        result = asyncio.run(
            trip_monitor._fetch_weather_for_segments(
                segments,
                average_speed_mps=10,
            )
        )

        assert result == {1: forecast}
        weather.assert_awaited_once()

        kwargs = weather.await_args.kwargs
        assert kwargs["latitude"] == 12.01
        assert kwargs["longitude"] == 75.01
        assert isinstance(kwargs["arrival_time"], datetime)


def test_weather_failure_returns_unknown_forecast():
    segments = [
        {
            "segment_id": 1,
            "length_m": 1000,
            "coordinates": [[75.0, 12.0], [75.01, 12.01]],
        }
    ]

    with patch.object(
        trip_monitor,
        "get_weather_forecast",
        new_callable=AsyncMock,
        side_effect=trip_monitor.WeatherForecastError(
            "Forecast unavailable"
        ),
    ):

        result = asyncio.run(
            trip_monitor._fetch_weather_for_segments(
                segments,
                average_speed_mps=10,
            )
        )

        assert result == {1: None}


# Risk escalation integration tests

def test_assess_upcoming_route_triggers_escalation():
    trip = make_trip()

    assessed_segments = [
        {
            "segment_id": 2,
            "risk_assessment": "complete",
            "score": 60,
            "level": "Orange",
        }
    ]

    with patch.object(
        trip_monitor,
        "_get_upcoming_segments",
        return_value=([{"segment_id": 2}], 10.0),
    ), patch.object(
        trip_monitor.asyncio,
        "run",
        return_value={2: {"precipitation_mm": 20}},
    ), patch.object(
        trip_monitor,
        "assess_route_segments",
        return_value=assessed_segments,
    ) as assess, patch.object(
        trip_monitor,
        "check_trip_risk_escalation",
        return_value=True,
    ) as escalation:

        trip_monitor._assess_upcoming_route(MagicMock(), trip)

        assess.assert_called_once()
        escalation.assert_called_once_with(
            assess.call_args.args[0],
            trip,
            "Orange",
        )


def test_incomplete_route_assessment_does_not_escalate():
    trip = make_trip()

    assessed_segments = [
        {
            "segment_id": 2,
            "risk_assessment": "incomplete",
            "score": None,
            "level": None,
        }
    ]

    with patch.object(
        trip_monitor,
        "_get_upcoming_segments",
        return_value=([{"segment_id": 2}], 10.0),
    ), patch.object(
        trip_monitor.asyncio,
        "run",
        return_value={2: None},
    ), patch.object(
        trip_monitor,
        "assess_route_segments",
        return_value=assessed_segments,
    ), patch.object(
        trip_monitor,
        "check_trip_risk_escalation",
    ) as escalation:

        trip_monitor._assess_upcoming_route(MagicMock(), trip)

        escalation.assert_not_called()
