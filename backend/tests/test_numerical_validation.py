from unittest.mock import Mock

import pytest

from backend.app.services.risk_service import assess_segment_risk
from backend.app.services.route_service import create_segments


@pytest.mark.parametrize("coordinate", [
    [float("nan"), 12.0],
    [float("inf"), 12.0],
    [181.0, 12.0],
    [75.0, 91.0],
])
def test_risk_service_rejects_invalid_coordinates(coordinate):
    with pytest.raises(ValueError):
        assess_segment_risk(
            Mock(), start=coordinate, end=[75.01, 12.01]
        )


@pytest.mark.parametrize("proximity", [
    float("nan"), float("inf"), 0, -1, True
])
def test_risk_service_rejects_invalid_proximity(proximity):
    with pytest.raises(ValueError, match="proximity_m"):
        assess_segment_risk(
            Mock(),
            start=[75.0, 12.0],
            end=[75.01, 12.01],
            proximity_m=proximity,
        )


@pytest.mark.parametrize("coordinates", [
    [[float("nan"), 12.0], [75.01, 12.01]],
    [[181.0, 12.0], [75.01, 12.01]],
    [[75.0, 91.0], [75.01, 12.01]],
])
def test_route_segmentation_rejects_invalid_coordinates(coordinates):
    with pytest.raises(ValueError, match="coordinate"):
        create_segments(coordinates, [100.0])


@pytest.mark.parametrize("distance", [
    float("nan"), float("inf"), -1, True
])
def test_route_segmentation_rejects_invalid_edge_distances(distance):
    with pytest.raises(ValueError, match="edge distance"):
        create_segments(
            [[75.0, 12.0], [75.01, 12.01]],
            [distance],
        )


def test_route_segmentation_accepts_zero_coordinates():
    segments = create_segments(
        [[0.0, 0.0], [0.01, 0.01]],
        [100.0],
    )
    assert segments
