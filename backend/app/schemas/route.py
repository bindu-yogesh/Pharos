from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class Coordinate(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class RouteRequest(BaseModel):
    origin: Coordinate
    destination: Coordinate
    district: str | None = Field(default=None, min_length=1)
    observation_date: date | None = None

    @model_validator(mode="after")
    def validate_weather_parameters(self):
        if (self.district is None) != (self.observation_date is None):
            raise ValueError(
                "district and observation_date must be provided together"
            )
        return self


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


class RouteResponse(BaseModel):
    distance_m: float | None = None
    duration_s: float | None = None
    district: str | None = None
    rainfall_mm: float | None = None
    weather_observation_date: date | None = None
    segments: list[RiskSegmentResponse] = Field(default_factory=list)
