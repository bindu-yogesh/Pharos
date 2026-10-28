
from unittest.mock import Mock

import pytest

from backend.app.services import risk_service


def test_complete_assessment_uses_existing_scorer(monkeypatch):
    db = Mock()
    db.scalar.side_effect = [1, 2]

    expected = {
        "score": 65,
        "level": "Orange",
        "reasons": ["Heavy rain", "Recent hazard report"],
    }
    scorer = Mock(return_value=expected)
    monkeypatch.setattr(risk_service, "calculate_risk", scorer)

    result = risk_service.assess_segment_risk(
        db,
        start=[75.0, 12.0],
        end=[75.01, 12.01],
        slope_percent=5.0,
        slope_threshold_percent=6.0,
        heavy_rain=True,
        low_visibility=False,
        heavy_traffic=False,
    )

    assert result["risk_assessment"] == "complete"
    assert result["risk_flags"] == {
        "heavy_rain": True,
        "landslide_history": True,
        "steep_slope": False,
        "recent_hazard_report": True,
        "heavy_traffic": False,
        "low_visibility": False,
    }
    scorer.assert_called_once_with(
        heavy_rain=True,
        landslide_history=True,
        steep_slope=False,
        recent_hazard_report=True,
        heavy_traffic=False,
        low_visibility=False,
    )
    assert result["score"] == 65


def test_unknown_inputs_do_not_generate_a_score(monkeypatch):
    db = Mock()
    db.scalar.side_effect = [None, None]
    scorer = Mock()
    monkeypatch.setattr(risk_service, "calculate_risk", scorer)

    result = risk_service.assess_segment_risk(
        db,
        start=[75.0, 12.0],
        end=[75.01, 12.01],
    )

    assert result["risk_assessment"] == "incomplete"
    assert result["score"] is None
    assert result["level"] is None
    assert set(result["risk_data_gaps"]) == {
        "heavy_rain",
        "steep_slope",
        "heavy_traffic",
        "low_visibility",
    }
    scorer.assert_not_called()


def test_invalid_proximity_is_rejected():
    with pytest.raises(ValueError, match="proximity_m"):
        risk_service.assess_segment_risk(
            Mock(),
            start=[75.0, 12.0],
            end=[75.01, 12.01],
            proximity_m=0,
        )


def test_invalid_slope_threshold_is_rejected():
    with pytest.raises(ValueError, match="slope_threshold_percent"):
        risk_service.assess_segment_risk(
            Mock(),
            start=[75.0, 12.0],
            end=[75.01, 12.01],
            slope_percent=5.0,
            slope_threshold_percent=0,
            heavy_rain=False,
            low_visibility=False,
            heavy_traffic=False,
        )
