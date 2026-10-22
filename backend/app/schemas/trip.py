from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class TripStartRequest(BaseModel):
    route_json: dict = Field(
        ...,
        description="Route details stored for this trip",
    )


class TripEndRequest(BaseModel):
    status: Literal["ended"] = "ended"


class TripResponse(BaseModel):
    id: int
    user_id: int
    route_json: dict
    status: Literal["active", "ended"]
    started_at: datetime
    ended_at: datetime | None = None