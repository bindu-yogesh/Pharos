
from risk_engine.score_route import score_route_segments


def test_all_route_segments_are_scored():
    results = score_route_segments()

    assert len(results) == 28


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
    assert segment_8["risk_score"] is None
    assert segment_8["known_risk_score"] == 20
    assert segment_8["risk_status"] == "incomplete"
    assert "heavy_rain" in segment_8["missing_factors"]
    assert "Steep slope" in segment_8["reasons"]


def test_non_steep_segment_gets_no_slope_points():
    results = score_route_segments()

    segment_1 = next(
        segment
        for segment in results
        if segment["segment_id"] == 1
    )

    assert abs(segment_1["slope_percent"]) < 6.0
    assert segment_1["risk_score"] is None
    assert segment_1["known_risk_score"] == 0
    assert segment_1["risk_status"] == "incomplete"
    assert segment_1["reasons"] == []
'''Test 1: Every segment in the current dataset receives a result.
Test 2: Every result contains the fields our future API will need.
Test 3: A steep segment activates the slope rule and receives its configured 20 points.
Test 4: A non-steep segment doesn't receive slope points.'''


def test_landslide_history_requires_complete_location_coverage(monkeypatch):
    import risk_engine.score_route as route

    segment = {
        "segment_id": 1,
        "length_m": 1000,
        "slope_percent": 0,
    }

    monkeypatch.setattr(route, "load_route_segments", lambda: [segment])

    cases = [
        (
            "matched",
            [{"id": "INC001", "type": "landslide",
              "latitude": 12.880, "longitude": 75.715}],
            ["INC001"],
            True,
        ),
        (
            "complete_no_match",
            [{"id": "INC001", "type": "landslide",
              "latitude": 12.880, "longitude": 75.715}],
            [],
            False,
        ),
        (
            "missing_coordinates",
            [{"id": "INC001", "type": "landslide",
              "latitude": None, "longitude": None}],
            [],
            None,
        ),
        (
            "empty_dataset",
            [],
            [],
            None,
        ),
    ]

    for case_name, incidents, matched_ids, expected in cases:
        monkeypatch.setattr(
            route, "load_incidents", lambda incidents=incidents: incidents
        )
        monkeypatch.setattr(
            route,
            "match_incidents_to_segments",
            lambda incidents, segments, max_distance_m, ids=matched_ids:
                {1: ids},
        )

        result = route.score_route_segments()[0]

        if expected is True:
            assert "Landslide history" in result["reasons"], case_name
            assert "landslide_history" not in result["missing_factors"]
        elif expected is False:
            assert "Landslide history" not in result["reasons"], case_name
            assert "landslide_history" not in result["missing_factors"]
        else:
            assert "landslide_history" in result["missing_factors"], case_name
