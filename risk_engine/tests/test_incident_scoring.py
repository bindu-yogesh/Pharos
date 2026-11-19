
from risk_engine.score_route import score_route_segments


def test_unlocated_incidents_do_not_increase_segment_scores():
    results = score_route_segments()

    assert len(results) == 28

    for segment in results:
        assert segment["historical_incident_ids"] == []
        assert "Landslide history" not in segment["reasons"]


def test_segment_results_include_incident_ids():
    results = score_route_segments()

    for segment in results:
        assert "historical_incident_ids" in segment
        assert isinstance(segment["historical_incident_ids"], list)
