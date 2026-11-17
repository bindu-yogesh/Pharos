from datetime import datetime, timezone

import httpx

from risk_engine import live_providers as providers


class MockResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


def test_weather_provider_matches_forecast_to_segment_eta():
    eta = datetime(2026, 11, 17, 15, 30, tzinfo=timezone.utc)
    payload = [{
        "hourly": {
            "time": ["2026-11-17T21:00", "2026-11-17T22:00"],
            "precipitation": [9.0, 1.0],
            "visibility": [800.0, 5000.0],
        }
    }]
    calls = []

    class Client:
        @staticmethod
        def get(url, **kwargs):
            calls.append((url, kwargs))
            return MockResponse(payload)

    segment = {
        "segment_id": 1,
        "start": [75.7, 12.8],
        "end": [75.8, 12.9],
    }

    result = providers.fetch_weather_for_segments([segment], [eta], Client())[0]

    assert result["heavy_rain"] is True
    assert result["low_visibility"] is True
    assert result["precipitation_mm"] == 9.0
    assert result["visibility_m"] == 800.0
    assert result["source"] == "Open-Meteo"
    assert len(calls) == 1


def test_weather_provider_returns_unknown_for_unmatched_forecast():
    eta = datetime(2026, 11, 20, tzinfo=timezone.utc)

    class Client:
        @staticmethod
        def get(url, **kwargs):
            return MockResponse([{
                "hourly": {
                    "time": ["2026-11-17T21:00"],
                    "precipitation": [0.0],
                    "visibility": [10000.0],
                }
            }])

    segment = {"start": [75.7, 12.8], "end": [75.8, 12.9]}

    assert providers.fetch_weather_for_segments(
        [segment], [eta], Client()
    ) == [None]


def test_weather_provider_handles_malformed_payload():
    class Client:
        @staticmethod
        def get(url, **kwargs):
            return MockResponse({"unexpected": "payload"})

    segment = {"start": [75.7, 12.8], "end": [75.8, 12.9]}
    eta = datetime.now(timezone.utc)

    assert providers.fetch_weather_for_segments(
        [segment], [eta], Client()
    ) == [None]


def test_traffic_provider_parses_confident_heavy_traffic(monkeypatch):
    monkeypatch.setenv("TOMTOM_API_KEY", "test-key")
    providers._cache.clear()

    class Client:
        @staticmethod
        def get(url, **kwargs):
            return MockResponse({
                "flowSegmentData": {
                    "currentSpeed": 15,
                    "freeFlowSpeed": 60,
                    "confidence": 0.9,
                    "roadClosure": False,
                }
            })

    result = providers.fetch_traffic_for_segment(12.8, 75.7, Client())

    assert result["heavy_traffic"] is True
    assert result["current_speed_kmph"] == 15.0
    assert result["confidence"] == 0.9
    assert result["source"] == "TomTom Traffic"


def test_traffic_provider_rejects_low_confidence(monkeypatch):
    monkeypatch.setenv("TOMTOM_API_KEY", "test-key")
    providers._cache.clear()

    class Client:
        @staticmethod
        def get(url, **kwargs):
            return MockResponse({
                "flowSegmentData": {
                    "currentSpeed": 15,
                    "freeFlowSpeed": 60,
                    "confidence": 0.2,
                    "roadClosure": False,
                }
            })

    assert providers.fetch_traffic_for_segment(12.8, 75.7, Client()) is None


def test_traffic_provider_returns_unknown_without_api_key(monkeypatch):
    monkeypatch.delenv("TOMTOM_API_KEY", raising=False)
    assert providers.fetch_traffic_for_segment(12.8, 75.7) is None


def test_traffic_provider_uses_short_cache(monkeypatch):
    monkeypatch.setenv("TOMTOM_API_KEY", "test-key")
    providers._cache.clear()
    calls = []

    class Client:
        @staticmethod
        def get(url, **kwargs):
            calls.append(1)
            return MockResponse({
                "flowSegmentData": {
                    "currentSpeed": 50,
                    "freeFlowSpeed": 60,
                    "confidence": 0.9,
                    "roadClosure": False,
                }
            })

    first = providers.fetch_traffic_for_segment(12.8, 75.7, Client())
    second = providers.fetch_traffic_for_segment(12.8, 75.7, Client())

    assert first == second
    assert len(calls) == 1


def test_recent_hazard_database_failure_returns_unknown(monkeypatch):
    import backend.app.database as database

    class BrokenSession:
        def __enter__(self):
            raise RuntimeError("database unavailable")

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(database, "SessionLocal", BrokenSession)

    result = providers.fetch_recent_hazard_matches([])

    assert result is None
