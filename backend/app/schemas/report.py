from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


ReportType = Literal["landslide", "falling_rock", "blockage"]
ReportStatus = Literal["active", "cleared", "rejected"]


class ReportCreate(BaseModel):
    type: ReportType
    severity: int = Field(ge=1, le=3)
    description: str | None = Field(default=None, max_length=500)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    photo_url: str | None = Field(default=None, max_length=500)


class ReportResponse(BaseModel):
    id: int
    user_id: int
    type: ReportType
    severity: int
    description: str | None
    photo_url: str | None
    latitude: float
    longitude: float
    status: ReportStatus
    created_at: datetime
    expires_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class ReportVoteCreate(BaseModel):
    vote: Literal["confirm", "clear"]


class ReportListResponse(ReportResponse):
    confirm_votes: int
    clear_votes: int
