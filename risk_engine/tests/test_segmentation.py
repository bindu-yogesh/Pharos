import pytest

from risk_engine.segmentation import calculate_slope, create_segments


def test_calculate_slope():
    slope = calculate_slope(
        elevation_start=400,
        elevation_end=430,
        length_m=1000,
    )

    assert slope == 3.0


def test_flat_segment():
    slope = calculate_slope(
        elevation_start=400,
        elevation_end=400,
        length_m=1000,
    )

    assert slope == 0.0


def test_downhill_segment():
    slope = calculate_slope(
        elevation_start=500,
        elevation_end=450,
        length_m=1000,
    )

    assert slope == -5.0


def test_invalid_segment_length():
    with pytest.raises(ValueError):
        calculate_slope(
            elevation_start=400,
            elevation_end=430,
            length_m=0,
        )


def test_create_segments():
    points = [
        (12.82, 75.53),
        (12.83, 75.54),
        (12.84, 75.55),
    ]

    segments = create_segments(points)

    assert len(segments) == 2
    assert segments[0]["segment_id"] == 1
    assert segments[1]["segment_id"] == 2
    assert segments[0]["length_m"] == 1000