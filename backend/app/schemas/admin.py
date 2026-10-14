from pydantic import BaseModel, Field


class UserBlockRequest(BaseModel):
    is_blocked: bool


class IncidentUpdateRequest(BaseModel):
    type: str | None = None
    location_name: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=2000)


class AdminStatsResponse(BaseModel):
    total_users: int
    total_reports: int
    active_reports: int
    cleared_reports: int
    rejected_reports: int