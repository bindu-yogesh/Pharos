
import pytest

from risk_engine.incident_matching import (
    distance_to_segment_m,
    match_incidents_to_segments,
)


@pytest.fixture
def segments():
    return [
        {
            "segment_id": 1,
            "start": [75.720, 12.880],
            "end": [75.710, 12.880],
            "length_m": 1000,
        },
        {
            "segment_id": 2,
            "start": [75.710, 12.880],
            "end": [75.700, 12.880],
            "length_m": 1000,
        },
    ]


def test_point_on_segment_has_near_zero_distance(segments):
    distance = distance_to_segment_m(
        12.880,
        75.715,
        segments[0],
    )
    assert distance < 1


def test_incident_matches_nearest_segment(segments):
    incidents = [
        {
            "id": "INC001",
            "latitude": 12.880,
            "longitude": 75.715,
        }
    ]

    matches = match_incidents_to_segments(
        incidents,
        segments,
        max_distance_m=500,
    )

    assert matches[1] == ["INC001"]
    assert matches[2] == []


def test_incidents_without_coordinates_are_ignored(segments):
    incidents = [
        {
            "id": "INC002",
            "latitude": None,
            "longitude": None,
        }
    ]

    matches = match_incidents_to_segments(incidents, segments)

    assert matches == {1: [], 2: []}


def test_incident_outside_matching_radius_is_ignored(segments):
    incidents = [
        {
            "id": "INC003",
            "latitude": 13.000,
            "longitude": 75.715,
        }
    ]

    matches = match_incidents_to_segments(
        incidents,
        segments,
        max_distance_m=100,
    )

    assert matches == {1: [], 2: []}


def test_negative_matching_radius_is_rejected(segments):
    with pytest.raises(ValueError):
        match_incidents_to_segments(
            [],
            segments,
            max_distance_m=-1,
        )
