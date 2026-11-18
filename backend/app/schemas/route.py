from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


RiskLevel = Literal["Green", "Yellow", "Orange", "Red"]
RiskAssessmentStatus = Literal["complete", "incomplete"]


class Coordinate(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class RouteRequest(BaseModel):
    origin: Coordinate
    destination: Coordinate
    district: str | None = Field(default=None, min_length=1)
    observation_date: date | None = None
    include_live_data: bool = False

    @model_validator(mode="after")
    def validate_weather_parameters(self):
        if (self.district is None) != (self.observation_date is None):
            raise ValueError(
                "district and observation_date must be provided together"
            )
        return self



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
    risk_score: float | None = Field(default=None, ge=0)
    risk_level: Literal["Green", "Yellow", "Orange", "Red"] | None = None
    known_risk_score: float | None = Field(default=None, ge=0)
    risk_status: Literal["complete", "incomplete"] = "complete"
    missing_factors: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    latitude: float | None = None
    longitude: float | None = None
    visibility_m: float | None = None
    traffic: dict | None = None
    historical_incident_ids: list[str] = Field(default_factory=list)
    recent_hazard_report_ids: list[str] = Field(default_factory=list)
    data_sources: dict = Field(default_factory=dict)


class RouteResponse(BaseModel):
    distance_m: float | None = None
    duration_s: float | None = None
    district: str | None = None
    rainfall_mm: float | None = None
    weather_observation_date: str | None = None
    segments: list[RiskSegmentResponse] = Field(default_factory=list)


class RouteOptionSegmentResponse(BaseModel):
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
    segments: list[RouteOptionSegmentResponse] = Field(default_factory=list)
    risk_assessment: RiskAssessmentStatus
    risk_data_gaps: list[str] = Field(default_factory=list)
    overall_risk_score: float | None = Field(default=None, ge=0, le=100)
    overall_risk_level: RiskLevel | None = None
    overall_risk_color: Literal["green", "yellow", "orange", "red"] | None = None
    overall_risk_reasons: list[str] = Field(default_factory=list)


class RouteCollectionResponse(BaseModel):
    routes: list[RouteOptionResponse] = Field(default_factory=list)
