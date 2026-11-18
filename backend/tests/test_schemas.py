
import pytest
from pydantic import ValidationError

from backend.app.schemas.report import ReportCreate, ReportVoteCreate
from backend.app.schemas.route import Coordinate


def test_report_rejects_invalid_severity():
    with pytest.raises(ValidationError):
        ReportCreate(
            type="landslide",
            severity=4,
            latitude=12.85,
            longitude=75.65,
        )


def test_vote_rejects_invalid_value():
    with pytest.raises(ValidationError):
        ReportVoteCreate(vote="maybe")


def test_coordinate_rejects_invalid_latitude():
    with pytest.raises(ValidationError):
        Coordinate(latitude=91, longitude=75.65)


def test_report_rejects_description_over_500_characters():
    with pytest.raises(ValidationError):
        ReportCreate(
            type="landslide",
            severity=2,
            description="x" * 501,
            latitude=12.85,
            longitude=75.65,
        )
