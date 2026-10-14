from pydantic import BaseModel, Field
from typing import Literal


class Coordinate(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class RouteRequest(BaseModel):
    origin: Coordinate
    destination: Coordinate

class RiskSegmentResponse(BaseModel):
    segment_id: int
    risk_score: float = Field(ge=0)
    risk_level: Literal["Green", "Yellow", "Orange", "Red"]
    reasons: list[str] = Field(default_factory=list)
    latitude: float | None = None
    longitude: float | None = None


class RouteResponse(BaseModel):
    distance_m: float | None = None
    duration_s: float | None = None
    segments: list[RiskSegmentResponse] = Field(default_factory=list)