from pydantic import BaseModel, Field


class TripLocationUpdate(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class TripLocationResponse(BaseModel):
    message: str
    trip_id: int
    alerts_sent: int