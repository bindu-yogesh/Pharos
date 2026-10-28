import pytest

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
