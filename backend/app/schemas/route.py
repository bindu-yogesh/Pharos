
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


RiskLevel = Literal["Green", "Yellow", "Orange", "Red"]
RiskAssessmentStatus = Literal["complete", "incomplete"]


class Coordinate(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class RouteRequest(BaseModel):
    origin: Coordinate
    destination: Coordinate


class LineStringGeometry(BaseModel):
    type: Literal["LineString"] = "LineString"
    coordinates: list[list[float]] = Field(min_length=2)


class RiskFlagsResponse(BaseModel):
    heavy_rain: bool | None
    landslide_history: bool | None
    steep_slope: bool | None
    recent_hazard_report: bool | None
    heavy_traffic: bool | None
    low_visibility: bool | None


class RiskSegmentResponse(BaseModel):
    segment_id: int
    start: list[float]
    end: list[float]
    coordinates: list[list[float]]
    geometry: LineStringGeometry
    length_m: float = Field(ge=0)

    risk_status: str
    risk_assessment: RiskAssessmentStatus

    road_segment_id: int | None = None
    road_match_distance_m: float | None = None
    slope_percent: float | None = None
    weather_forecast: dict | None = None

    score: float | None = Field(default=None, ge=0, le=100)
    level: RiskLevel | None = None
    color: Literal["green", "yellow", "orange", "red"] | None = None

    risk_flags: RiskFlagsResponse | None = None
    reasons: list[str] = Field(default_factory=list)
    risk_data_gaps: list[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class RouteOptionResponse(BaseModel):
    distance_m: float = Field(ge=0)
    duration_s: float = Field(ge=0)
    geometry: LineStringGeometry
    segments: list[RiskSegmentResponse] = Field(default_factory=list)

    risk_assessment: RiskAssessmentStatus
    risk_data_gaps: list[str] = Field(default_factory=list)

    overall_risk_score: float | None = Field(default=None, ge=0, le=100)
    overall_risk_level: RiskLevel | None = None
    overall_risk_color: Literal[
        "green", "yellow", "orange", "red"
    ] | None = None
    overall_risk_reasons: list[str] = Field(default_factory=list)


class RouteCollectionResponse(BaseModel):
    routes: list[RouteOptionResponse] = Field(default_factory=list)
