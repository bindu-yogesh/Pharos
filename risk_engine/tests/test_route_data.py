import json
from pathlib import Path


DATA_FILE = Path("data/route_segments_with_slope.json")


def load_segments():
    with open(DATA_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def test_route_segments_exist():
    segments = load_segments()

    assert len(segments) == 18


def test_segment_ids_are_sequential():
    segments = load_segments()

    ids = [segment["segment_id"] for segment in segments]

    assert ids == list(range(1, 19))


def test_required_fields_exist():
    segments = load_segments()

    required_fields = {
        "segment_id",
        "start",
        "end",
        "length_m",
        "elevation_start_m",
        "elevation_end_m",
        "slope_percent",
    }

    for segment in segments:
        assert required_fields.issubset(segment.keys())


def test_segment_lengths_are_positive():
    segments = load_segments()

    for segment in segments:
        assert segment["length_m"] > 0


def test_elevation_values_exist():
    segments = load_segments()

    for segment in segments:
        assert segment["elevation_start_m"] is not None
        assert segment["elevation_end_m"] is not None


def test_adjacent_elevations_match():
    segments = load_segments()

    for i in range(len(segments) - 1):
        current = segments[i]
        next_segment = segments[i + 1]

        assert (
            current["elevation_end_m"]
            == next_segment["elevation_start_m"]
        )


def test_slope_values_exist():
    segments = load_segments()

    for segment in segments:
        assert segment["slope_percent"] is not None