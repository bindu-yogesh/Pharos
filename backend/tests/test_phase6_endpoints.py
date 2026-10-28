import pytest
from unittest.mock import AsyncMock, patch

from backend.app.integrations.osrm import OSRMError
from geoalchemy2 import WKTElement

from backend.app.models.segment import RoadSegment
from backend.app.routers.routes import (
    calculate_bearing,
    calculate_bearing_difference,
)

def get_auth_headers(client, email):
    password = "TestPassword123!"
    registration = client.post(
        "/auth/register",
        json={
            "name": "Phase 6 Driver",
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
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_route_success(client):
    osrm_route = {
        "distance": 1500,
        "duration": 120,
        "geometry": {
            "type": "LineString",
            "coordinates": [[75.0, 12.0], [75.01, 12.0], [75.02, 12.0]],
        },
        "legs": [{"annotation": {"distance": [800, 700]}}],
    }

    with patch(
        "backend.app.routers.routes.get_route",
        new_callable=AsyncMock,
        return_value={"code": "Ok", "routes": [osrm_route]},
    ):
        response = client.post(
            "/route",
            json={
                "origin": {"latitude": 12.0, "longitude": 75.0},
                "destination": {"latitude": 12.0, "longitude": 75.02},
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["routes"][0]["distance_m"] == 1500
    assert body["routes"][0]["risk_assessment"] == "incomplete"


def test_route_osrm_failure(client):
    with patch(
        "backend.app.routers.routes.get_route",
        new_callable=AsyncMock,
        side_effect=OSRMError("OSRM unavailable"),
    ):
        response = client.post(
            "/route",
            json={
                "origin": {"latitude": 12.0, "longitude": 75.0},
                "destination": {"latitude": 12.1, "longitude": 75.1},
            },
        )

    assert response.status_code == 502


def test_risk_validation_and_unavailable_status(client):
    invalid = client.get("/risk", params={"lat": 91, "lon": 75})
    assert invalid.status_code == 422

    response = client.get("/risk", params={"lat": 12, "lon": 75})
    assert response.status_code == 200
    assert response.json()["risk_score"] is None
    assert response.json()["risk_assessment"] == "incomplete"

def test_trip_start_requires_authentication(client):
    response = client.post(
        "/trips/start",
        json={"route_json": {"distance_m": 1000}},
    )
    assert response.status_code == 401


def test_trip_start_and_end(client):
    headers = get_auth_headers(client, "phase6-lifecycle@example.com")

    start = client.post(
        "/trips/start",
        headers=headers,
        json={"route_json": {"distance_m": 1000}},
    )
    assert start.status_code == 201
    trip = start.json()
    assert trip["status"] == "active"

    end = client.post(
        f"/trips/{trip['id']}/end",
        headers=headers,
        json={"status": "ended"},
    )
    assert end.status_code == 200
    assert end.json()["status"] == "ended"
    assert end.json()["ended_at"] is not None


def test_trip_ownership_and_duplicate_active_trip(client):
    owner = get_auth_headers(client, "phase6-owner@example.com")
    other = get_auth_headers(client, "phase6-other@example.com")

    start = client.post(
        "/trips/start",
        headers=owner,
        json={"route_json": {"distance_m": 1000}},
    )
    assert start.status_code == 201

    duplicate = client.post(
        "/trips/start",
        headers=owner,
        json={"route_json": {"distance_m": 2000}},
    )
    assert duplicate.status_code == 409

    wrong_owner_end = client.post(
        f"/trips/{start.json()['id']}/end",
        headers=other,
        json={"status": "ended"},
    )
    assert wrong_owner_end.status_code == 404


def test_risk_matched_road_segment(client, db_session):
    segment = RoadSegment(
        segment_no=987655,
        geom=WKTElement(
            "LINESTRING(75.0 12.0, 75.01 12.0)",
            srid=4326,
        ),
        length_m=1000.0,
        elevation_start_m=100.0,
        elevation_end_m=102.0,
        slope_percent=0.2,
    )
    db_session.add(segment)
    db_session.flush()

    response = client.get(
        "/risk",
        params={"lat": 12.0, "lon": 75.005},
    )

    assert response.status_code == 200
    body = response.json()

    assert body["road_segment_id"] == segment.id
    assert body["road_match_distance_m"] == 0.0
    assert body["risk_assessment"] == "incomplete"
    assert body["risk_score"] is None
    assert body["risk_level"] is None
    assert "heavy_rain" in body["risk_data_gaps"]
    assert "low_visibility" in body["risk_data_gaps"]
    assert "heavy_traffic" in body["risk_data_gaps"]


def test_risk_unmatched_location_returns_no_score(client):
    response = client.get(
        "/risk",
        params={"lat": 0.0, "lon": 0.0},
    )

    assert response.status_code == 200
    body = response.json()

    assert body["risk_assessment"] == "incomplete"
    assert body["risk_score"] is None
    assert body["risk_level"] is None
    assert body["reasons"] == []
    assert any(
        "No stored road segment found" in gap
        for gap in body["risk_data_gaps"]
    )

def test_calculate_bearing_directions():
    north = calculate_bearing(75.0, 12.0, 75.0, 13.0)
    east = calculate_bearing(75.0, 12.0, 76.0, 12.0)

    assert north == pytest.approx(0.0, abs=0.01)
    assert east == pytest.approx(90.0, abs=0.2)


def test_two_way_heading_difference():
    assert calculate_bearing_difference(0.0, 0.0) == 0.0
    assert calculate_bearing_difference(0.0, 180.0) == 0.0


def test_heading_difference_wraps_at_north():
    assert calculate_bearing_difference(0.0, 355.0) == 5.0
    assert calculate_bearing_difference(0.0, 5.0) == 5.0
