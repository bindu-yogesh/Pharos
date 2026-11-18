from risk_engine.score_route import score_route_segments


def test_all_route_segments_are_returned():
    results = score_route_segments()
    assert len(results) == 28


def test_every_segment_has_required_risk_fields():
    results = score_route_segments()

    required_fields = {
        "segment_id",
        "length_m",
        "slope_percent",
        "risk_assessment",
        "risk_data_gaps",
        "risk_score",
        "risk_level",
        "reasons",
    }

    for segment in results:
        assert required_fields.issubset(segment.keys())


def test_route_segments_without_all_risk_inputs_are_incomplete():
    results = score_route_segments()

    assert all(
        segment["risk_assessment"] == "incomplete"
        and segment["risk_score"] is None
        and segment["risk_level"] is None
        for segment in results
    )


def test_incomplete_route_segments_do_not_claim_no_risk():
    results = score_route_segments()

    assert all(segment["risk_score"] is None for segment in results)
