
from risk_engine.score_route import score_route_segments


def test_all_route_segments_are_scored():
    results = score_route_segments()

    assert len(results) == 18


def test_every_segment_has_required_risk_fields():
    results = score_route_segments()

    required_fields = {
        "segment_id",
        "length_m",
        "slope_percent",
        "risk_score",
        "risk_level",
        "reasons",
    }

    for segment in results:
        assert required_fields.issubset(segment.keys())


def test_steep_segment_receives_slope_points():
    results = score_route_segments()

    segment_8 = next(
        segment
        for segment in results
        if segment["segment_id"] == 8
    )

    assert abs(segment_8["slope_percent"]) >= 6.0
    assert segment_8["risk_score"] == 20
    assert "Steep slope" in segment_8["reasons"]


def test_non_steep_segment_gets_no_slope_points():
    results = score_route_segments()

    segment_1 = next(
        segment
        for segment in results
        if segment["segment_id"] == 1
    )

    assert abs(segment_1["slope_percent"]) < 6.0
    assert segment_1["risk_score"] == 0
    assert segment_1["reasons"] == []
'''Test 1: Every segment in the current dataset receives a result.
Test 2: Every result contains the fields our future API will need.
Test 3: A steep segment activates the slope rule and receives its configured 20 points.
Test 4: A non-steep segment doesn't receive slope points.'''
