import pytest
from fastapi.testclient import TestClient

import backend.app.routers.routes as route_api
import backend.app.routers.risk_routes as risk_route_api
from backend.app.main import app
from risk_engine.score_route import load_route_segments


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
        segments = load_route_segments()
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
                    "legs": [{
                        "annotation": {
                            "distance": [28566.4 / 28] * 28,
                        },
                    }],
                }
            ],
        }


def mock_osrm_success(monkeypatch):
    async def mocked_get_route(origin, destination, alternatives=True):
        reverse = origin == (75.542298, 12.831463)
        return MockOSRMResponse(reverse=reverse).json()

    def mocked_legacy_get(url, *args, **kwargs):
        reverse = url.split("/")[-1].startswith("75.542298,12.831463;")
        return MockOSRMResponse(reverse=reverse)

    monkeypatch.setattr(route_api, "get_route", mocked_get_route)
    monkeypatch.setattr(risk_route_api.httpx, "get", mocked_legacy_get)


@pytest.mark.parametrize("path", ["/route", "/routes/assess"])
def test_route_endpoints_return_success(path, monkeypatch):
    mock_osrm_success(monkeypatch)

    response = client.post(path, json=FORWARD_PAYLOAD)

    assert response.status_code == 200

    body = response.json()
    if path == "/route":
        body = body["routes"][0]
    assert body["distance_m"] == 28566.4
    assert body["duration_s"] == 1233.0
    assert len(body["segments"]) == 28
    assert body["segments"][0]["segment_id"] == 1
    assert body["segments"][-1]["segment_id"] == 28


def test_reverse_route_returns_segments_in_reverse_order(monkeypatch):
    mock_osrm_success(monkeypatch)

    response = client.post("/route", json=REVERSE_PAYLOAD)

    assert response.status_code == 200

    route = response.json()["routes"][0]
    segment_ids = [
        segment["segment_id"]
        for segment in route["segments"]
    ]

    assert segment_ids[0] == 1
    assert segment_ids[-1] == 28


def test_unsupported_corridor_is_rejected_before_osrm(monkeypatch):
    osrm_called = False

    async def unexpected_osrm_call(*args, **kwargs):
        nonlocal osrm_called
        osrm_called = True
        raise AssertionError("OSRM should not be called for an unsupported corridor")

    monkeypatch.setattr(route_api, "get_route", unexpected_osrm_call)

    payload = {
        "origin": {"latitude": 12.9716, "longitude": 77.5946},
        "destination": {"latitude": 13.0827, "longitude": 80.2707},
    }

    response = client.post("/routes/assess", json=payload)

    assert response.status_code == 422
    assert osrm_called is False


def test_weather_parameters_must_be_provided_together():
    payload = {
        **FORWARD_PAYLOAD,
        "district": "DAKSHIN KANNADA",
    }

    response = client.post("/routes/assess", json=payload)

    assert response.status_code == 422


def test_osrm_timeout_returns_gateway_timeout(monkeypatch):
    async def timeout(*args, **kwargs):
        raise route_api.OSRMTimeoutError("OSRM routing request timed out.")

    monkeypatch.setattr(route_api, "get_route", timeout)

    response = client.post("/route", json=FORWARD_PAYLOAD)

    assert response.status_code == 504
    assert "timed out" in response.json()["detail"]


def test_osrm_unsuccessful_route_returns_bad_gateway(monkeypatch):
    class FailedOSRMResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"code": "NoRoute", "routes": []}

    async def failed_route(*args, **kwargs):
        raise route_api.OSRMError("No valid route was found between these locations.")

    monkeypatch.setattr(route_api, "get_route", failed_route)

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

    response = client.post("/routes/assess", json=payload)

    assert response.status_code == 200

    body = response.json()
    assert body["rainfall_mm"] is None
    assert body["weather_observation_date"] is None


def test_live_data_request_passes_duration_and_returns_segment_metadata(monkeypatch):
    mock_osrm_success(monkeypatch)
    original_assessor = route_api.assess_route_segments

    def mocked_assessor(db, segments, **kwargs):
        results = original_assessor(db, segments, **kwargs)
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

    monkeypatch.setattr(route_api, "assess_route_segments", mocked_assessor)

    response = client.post(
        "/route",
        json={**FORWARD_PAYLOAD, "include_live_data": True},
    )

    assert response.status_code == 200
    route = response.json()["routes"][0]
    assert route["duration_s"] == 1233.0

    segment = next(
        item for item in route["segments"]
        if item["segment_id"] == 1
    )
    assert segment["visibility_m"] == 850.0
    assert segment["traffic"]["heavy_traffic"] is True
    assert segment["historical_incident_ids"] == ["H-1"]
    assert segment["recent_hazard_report_ids"] == ["R-1"]
    assert segment["data_sources"]["weather"] == "Open-Meteo"
def test_reverse_route_passes_reverse_flag_to_risk_scorer(monkeypatch):
    mock_osrm_success(monkeypatch)

    response = client.post("/route", json=REVERSE_PAYLOAD)

    assert response.status_code == 200
    route = response.json()["routes"][0]
    assert route["segments"][0]["segment_id"] == 1
    assert route["segments"][-1]["segment_id"] == 28


def test_forward_route_passes_forward_flag_to_risk_scorer(monkeypatch):
    mock_osrm_success(monkeypatch)

    response = client.post("/route", json=FORWARD_PAYLOAD)

    assert response.status_code == 200
    route = response.json()["routes"][0]
    assert route["segments"][0]["segment_id"] == 1
@pytest.mark.parametrize(
    "route_data",
    [
        {"duration": 100.0, "geometry": {"type": "LineString", "coordinates": [[75.721304, 12.879189], [75.542298, 12.831463]]}},
        {"distance": 1000.0, "geometry": {"type": "LineString", "coordinates": [[75.721304, 12.879189], [75.542298, 12.831463]]}},
        {"distance": -1.0, "duration": 100.0, "geometry": {"type": "LineString", "coordinates": [[75.721304, 12.879189], [75.542298, 12.831463]]}},
        {"distance": 1000.0, "duration": -1.0, "geometry": {"type": "LineString", "coordinates": [[75.721304, 12.879189], [75.542298, 12.831463]]}},
        {"distance": float("nan"), "duration": 100.0, "geometry": {"type": "LineString", "coordinates": [[75.721304, 12.879189], [75.542298, 12.831463]]}},
        {"distance": 1000.0, "duration": float("inf"), "geometry": {"type": "LineString", "coordinates": [[75.721304, 12.879189], [75.542298, 12.831463]]}},
        None,
    ],
)
def test_malformed_osrm_route_is_rejected(monkeypatch, route_data):
    class MalformedOSRMResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"code": "Ok", "routes": [route_data]}

    async def malformed_route(*args, **kwargs):
        return MalformedOSRMResponse().json()

    monkeypatch.setattr(route_api, "get_route", malformed_route)

    response = client.post("/route", json=FORWARD_PAYLOAD)

    assert response.status_code == 502
@pytest.mark.parametrize(
    "geometry",
    [
        None,
        {"type": "Point", "coordinates": [75.7, 12.8]},
        {"type": "LineString", "coordinates": [[float("nan"), 12.8], [75.5, 12.9]]},
        {"type": "LineString", "coordinates": [[10.0, 10.0], [11.0, 11.0]]},
    ],
)
def test_invalid_or_unmatched_osrm_geometry_is_rejected(monkeypatch, geometry):
    class InvalidGeometryResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "code": "Ok",
                "routes": [{
                    "distance": 1000.0,
                    "duration": 100.0,
                    "geometry": geometry,
                }],
            }

    async def invalid_geometry_route(*args, **kwargs):
        return InvalidGeometryResponse().json()

    monkeypatch.setattr(route_api, "get_route", invalid_geometry_route)

    response = client.post("/route", json=FORWARD_PAYLOAD)

    assert response.status_code == 502



def test_osrm_invalid_json_returns_bad_gateway(monkeypatch):
    class InvalidJSONResponse:
        def raise_for_status(self):
            pass

        def json(self):
            raise ValueError("simulated invalid JSON")

    async def invalid_json_route(*args, **kwargs):
        raise route_api.OSRMError("OSRM returned invalid JSON.")

    monkeypatch.setattr(route_api, "get_route", invalid_json_route)

    response = client.post("/route", json=FORWARD_PAYLOAD)

    assert response.status_code == 502
    assert response.json()["detail"] == "OSRM returned invalid JSON."
