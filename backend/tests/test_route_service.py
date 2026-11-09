import pytest
from backend.app.services.route_service import classify_weather_risk

from backend.app.services.route_service import create_segments, process_osrm_route


def test_create_segments_preserves_total_distance():
    coordinates = [[75.0, 12.0], [75.01, 12.0], [75.02, 12.0], [75.03, 12.0]]
    segments = create_segments(coordinates, [600, 500, 400], target_length_m=1000)

    assert len(segments) == 2
    assert sum(s["length_m"] for s in segments) == 1500
    assert segments[0]["start"] == coordinates[0]
    assert segments[0]["end"] == coordinates[2]
    assert segments[1]["end"] == coordinates[-1]
    assert all(s["risk_status"] == "not_assessed" for s in segments)


def test_create_segments_rejects_mismatched_edge_distances():
    with pytest.raises(ValueError, match="Edge-distance count"):
        create_segments([[75.0, 12.0], [75.1, 12.1]], [])


def test_create_segments_rejects_invalid_target_length():
    with pytest.raises(ValueError, match="greater than zero"):
        create_segments([[75.0, 12.0], [75.1, 12.1]], [100], 0)


def test_process_osrm_route_normalizes_route_and_marks_risk_unavailable():
    route = {
        "distance": 1500,
        "duration": 120,
        "geometry": {
            "type": "LineString",
            "coordinates": [[75.0, 12.0], [75.01, 12.0], [75.02, 12.0]],
        },
        "legs": [{"annotation": {"distance": [800, 700]}}],
    }

    result = process_osrm_route(route)

    assert result["distance_m"] == 1500
    assert result["duration_s"] == 120
    assert len(result["segments"]) == 1
    assert result["risk_assessment"] == "unavailable"
    assert result["risk_data_gaps"]


def test_process_osrm_route_rejects_missing_annotations():
    with pytest.raises(ValueError, match="missing geometry"):
        process_osrm_route({"distance": 100, "duration": 20})

def test_create_segments_preserves_intermediate_coordinates():
    coordinates = [
        [75.0, 12.0],
        [75.01, 12.0],
        [75.015, 12.005],
        [75.02, 12.01],
    ]

    segments = create_segments(
        coordinates,
        [400, 400, 400],
        target_length_m=1000,
    )

    assert len(segments) == 1
    segment = segments[0]

    assert segment["coordinates"] == coordinates
    assert segment["geometry"]["type"] == "LineString"
    assert segment["geometry"]["coordinates"] == coordinates
    assert segment["start"] == coordinates[0]
    assert segment["end"] == coordinates[-1]

def test_create_segments_preserves_geometry_across_boundaries():
    coordinates = [
        [75.0, 12.0],
        [75.01, 12.0],
        [75.015, 12.005],
        [75.02, 12.01],
    ]

    segments = create_segments(
        coordinates,
        [600, 500, 400],
        target_length_m=1000,
    )

    assert len(segments) == 2

    assert segments[0]["coordinates"] == coordinates[:3]
    assert segments[1]["coordinates"] == coordinates[2:]

    # Adjacent segments share their boundary coordinate.
    assert segments[0]["end"] == segments[1]["start"]

def test_create_segments_preserves_total_distance_with_geometry():
    coordinates = [
        [75.0, 12.0],
        [75.01, 12.0],
        [75.02, 12.0],
        [75.03, 12.0],
    ]

    segments = create_segments(
        coordinates,
        [600, 500, 400],
        target_length_m=1000,
    )

    assert sum(segment["length_m"] for segment in segments) == 1500
    assert segments[0]["length_m"] == 1100
    assert segments[1]["length_m"] == 400

def test_assess_route_segments_rejects_invalid_geometry(db_session):
    from backend.app.services.route_service import assess_route_segments

    segment = {
        "segment_id": 1,
        "start": [75.0, 12.0],
        "end": [75.0, 12.0],
        "coordinates": [[75.0, 12.0]],
        "length_m": 100,
    }

    with pytest.raises(ValueError, match="at least two coordinates"):
        assess_route_segments(db_session, [segment])

def test_process_osrm_route_preserves_segment_geometry():
    coordinates = [
        [75.0, 12.0],
        [75.01, 12.0],
        [75.015, 12.005],
    ]

    route = {
        "distance": 1200,
        "duration": 120,
        "geometry": {
            "type": "LineString",
            "coordinates": coordinates,
        },
        "legs": [{"annotation": {"distance": [600, 600]}}],
    }

    result = process_osrm_route(route)

    assert result["segments"][0]["coordinates"] == coordinates
    assert result["segments"][0]["geometry"]["coordinates"] == coordinates


from backend.app.services.route_service import (
    calculate_overall_route_risk,
    get_risk_level,
)


def test_risk_level_boundaries():
    assert get_risk_level(0) == "Green"
    assert get_risk_level(30) == "Green"
    assert get_risk_level(31) == "Yellow"
    assert get_risk_level(50) == "Yellow"
    assert get_risk_level(51) == "Orange"
    assert get_risk_level(75) == "Orange"
    assert get_risk_level(76) == "Red"
    assert get_risk_level(100) == "Red"


def test_overall_route_risk_uses_distance_weighted_average():
    segments = [
        {
            "length_m": 1000,
            "score": 20,
            "risk_assessment": "complete",
            "reasons": ["Low slope"],
        },
        {
            "length_m": 3000,
            "score": 60,
            "risk_assessment": "complete",
            "reasons": ["Heavy rain"],
        },
    ]

    result = calculate_overall_route_risk(segments)

    assert result["risk_assessment"] == "complete"
    assert result["overall_risk_score"] == 50
    assert result["overall_risk_level"] == "Yellow"
    assert result["overall_risk_color"] == "yellow"
    assert result["overall_risk_reasons"] == [
        "Heavy rain",
        "Low slope",
    ]


def test_overall_route_risk_is_incomplete_if_any_segment_is_incomplete():
    segments = [
        {
            "length_m": 1000,
            "score": 20,
            "risk_assessment": "complete",
            "reasons": [],
        },
        {
            "length_m": 1000,
            "score": None,
            "risk_assessment": "incomplete",
            "reasons": [],
        },
    ]

    result = calculate_overall_route_risk(segments)

    assert result["risk_assessment"] == "incomplete"
    assert result["overall_risk_score"] is None
    assert result["overall_risk_level"] is None
    assert result["overall_risk_color"] is None


def test_overall_route_risk_handles_empty_segments():
    result = calculate_overall_route_risk([])

    assert result["risk_assessment"] == "incomplete"
    assert result["overall_risk_score"] is None


def test_overall_route_risk_handles_zero_total_distance():
    segments = [
        {
            "length_m": 0,
            "score": 20,
            "risk_assessment": "complete",
            "reasons": [],
        },
    ]

    result = calculate_overall_route_risk(segments)

    assert result["risk_assessment"] == "incomplete"
    assert result["overall_risk_score"] is None


import pytest


@pytest.mark.parametrize(
    ("weather", "expected"),
    [
        ({"precipitation_mm": 15.1, "visibility_m": 5000}, (True, False)),
        ({"precipitation_mm": 15, "visibility_m": 5000}, (False, False)),
        ({"precipitation_mm": 0, "visibility_m": 999}, (False, True)),
        ({"precipitation_mm": 20, "visibility_m": 1000}, (True, False)),
        ({"precipitation_mm": 0, "visibility_m": 1000}, (False, False)),
        ({"precipitation_mm": None, "visibility_m": 500}, (None, True)),
        ({"precipitation_mm": 10, "visibility_m": None}, (False, None)),
        (None, (None, None)),
    ],
)
def test_classify_weather_risk(weather, expected):
    assert classify_weather_risk(weather) == expected


def test_classify_weather_risk_rejects_invalid_values():
    assert classify_weather_risk({
        "precipitation_mm": "invalid",
        "visibility_m": 500,
    }) == (None, None)


def test_classify_weather_risk_rejects_infinite_values():
    assert classify_weather_risk({
        "precipitation_mm": float("inf"),
        "visibility_m": float("nan"),
    }) == (None, None)
