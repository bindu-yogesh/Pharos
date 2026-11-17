import httpx
import pytest
from fastapi.testclient import TestClient

import backend.app.routers.routes as route_api
from backend.app.main import app


client = TestClient(app)

FORWARD_PAYLOAD = {
    "origin": {"latitude": 12.879189, "longitude": 75.721304},
    "destination": {"latitude": 12.831463, "longitude": 75.542298},
}

REVERSE_PAYLOAD = {
    "origin": {"latitude": 12.831463, "longitude": 75.542298},
    "destination": {"latitude": 12.879189, "longitude": 75.721304},
}


class MockOSRMResponse:
    def __init__(self, reverse=False):
        self.reverse = reverse

    def raise_for_status(self):
        pass

    def json(self):
        segments = route_api.load_route_segments()
        coordinates = [segments[0]["start"]] + [
            segment["end"] for segment in segments
        ]

        if self.reverse:
            coordinates.reverse()

        return {
            "code": "Ok",
            "routes": [
                {
                    "distance": 28566.4,
                    "duration": 1233.0,
                    "geometry": {
                        "type": "LineString",
                        "coordinates": coordinates,
                    },
                }
            ],
        }


def mock_osrm_success(monkeypatch):
    def mocked_get(url, *args, **kwargs):
        reverse = url.split("/")[-1].startswith("75.542298,12.831463;")
        return MockOSRMResponse(reverse=reverse)

    monkeypatch.setattr(route_api.httpx, "get", mocked_get)


@pytest.mark.parametrize("path", ["/route", "/routes/assess"])
def test_route_endpoints_return_success(path, monkeypatch):
    mock_osrm_success(monkeypatch)

    response = client.post(path, json=FORWARD_PAYLOAD)

    assert response.status_code == 200

    body = response.json()
    assert body["distance_m"] == 28566.4
    assert body["duration_s"] == 1233.0
    assert len(body["segments"]) == 28
    assert body["segments"][0]["segment_id"] == 1
    assert body["segments"][-1]["segment_id"] == 28


def test_reverse_route_returns_segments_in_reverse_order(monkeypatch):
    mock_osrm_success(monkeypatch)

    response = client.post("/route", json=REVERSE_PAYLOAD)

    assert response.status_code == 200

    segment_ids = [
        segment["segment_id"]
        for segment in response.json()["segments"]
    ]

    assert segment_ids[0] == 28
    assert segment_ids[-1] == 1


def test_unsupported_corridor_is_rejected_before_osrm(monkeypatch):
    osrm_called = False

    def unexpected_osrm_call(*args, **kwargs):
        nonlocal osrm_called
        osrm_called = True
        raise AssertionError("OSRM should not be called for an unsupported corridor")

    monkeypatch.setattr(route_api.httpx, "get", unexpected_osrm_call)

    payload = {
        "origin": {"latitude": 12.9716, "longitude": 77.5946},
        "destination": {"latitude": 13.0827, "longitude": 80.2707},
    }

    response = client.post("/route", json=payload)

    assert response.status_code == 422
    assert osrm_called is False


def test_weather_parameters_must_be_provided_together():
    payload = {
        **FORWARD_PAYLOAD,
        "district": "DAKSHIN KANNADA",
    }

    response = client.post("/route", json=payload)

    assert response.status_code == 422


def test_osrm_timeout_returns_gateway_timeout(monkeypatch):
    def timeout(*args, **kwargs):
        raise httpx.TimeoutException("simulated timeout")

    monkeypatch.setattr(route_api.httpx, "get", timeout)

    response = client.post("/route", json=FORWARD_PAYLOAD)

    assert response.status_code == 504
    assert "timed out" in response.json()["detail"]


def test_osrm_unsuccessful_route_returns_bad_gateway(monkeypatch):
    class FailedOSRMResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"code": "NoRoute", "routes": []}

    monkeypatch.setattr(
        route_api.httpx,
        "get",
        lambda *args, **kwargs: FailedOSRMResponse(),
    )

    response = client.post("/route", json=FORWARD_PAYLOAD)

    assert response.status_code == 502


def test_openapi_contains_both_route_paths():
    paths = app.openapi()["paths"]

    assert "/route" in paths
    assert "/routes/assess" in paths

def test_missing_weather_observation_returns_null_date_and_rainfall(monkeypatch):
    mock_osrm_success(monkeypatch)

    payload = {
        **FORWARD_PAYLOAD,
        "district": "UNKNOWN DISTRICT",
        "observation_date": "2026-11-16",
    }

    response = client.post("/route", json=payload)

    assert response.status_code == 200

    body = response.json()
    assert body["rainfall_mm"] is None
    assert body["weather_observation_date"] is None


def test_live_data_request_passes_duration_and_returns_segment_metadata(monkeypatch):
    mock_osrm_success(monkeypatch)
    original_scorer = route_api.score_route_segments
    captured = {}

    def mocked_scorer(**kwargs):
        captured.update(kwargs)
        results = original_scorer(
            district=kwargs["district"],
            observation_date=kwargs["observation_date"],
            include_live_data=False,
            route_duration_s=kwargs["route_duration_s"],
        )
        first = results[0]
        first.update({
            "visibility_m": 850.0,
            "traffic": {
                "heavy_traffic": True,
                "source": "TomTom Traffic",
            },
            "historical_incident_ids": ["H-1"],
            "recent_hazard_report_ids": ["R-1"],
            "data_sources": {
                "weather": "Open-Meteo",
                "traffic": "TomTom Traffic",
                "community_reports": "postgis",
            },
        })
        return results

    monkeypatch.setattr(
        route_api, "score_route_segments", mocked_scorer
    )

    response = client.post(
        "/route",
        json={**FORWARD_PAYLOAD, "include_live_data": True},
    )

    assert response.status_code == 200
    assert captured["include_live_data"] is True
    assert captured["route_duration_s"] == 1233.0

    segment = next(
        item for item in response.json()["segments"]
        if item["segment_id"] == 1
    )
    assert segment["visibility_m"] == 850.0
    assert segment["traffic"]["heavy_traffic"] is True
    assert segment["historical_incident_ids"] == ["H-1"]
    assert segment["recent_hazard_report_ids"] == ["R-1"]
    assert segment["data_sources"]["weather"] == "Open-Meteo"
