
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.trip import Trip
from ..schemas.trip import TripEndRequest, TripResponse, TripStartRequest
from ..security.deps import get_current_user

router = APIRouter(prefix="/trips", tags=["trips"])

DbSession = Annotated[Session, Depends(get_db)]


@router.post(
    "/start",
    response_model=TripResponse,
    status_code=status.HTTP_201_CREATED,
)
def start_trip(
    request: TripStartRequest,
    db: DbSession,
    current_user=Depends(get_current_user),
):
    active_trip = db.scalar(
        select(Trip).where(
            Trip.user_id == current_user.id,
            Trip.status == "active",
        )
    )

    if active_trip is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have an active trip.",
        )

    trip = Trip(
        user_id=current_user.id,
        route_json=request.route_json,
        status="active",
    )
    db.add(trip)
    db.commit()
    db.refresh(trip)
    return trip


@router.post("/{trip_id}/end", response_model=TripResponse)
def end_trip(
    trip_id: int,
    request: TripEndRequest,
    db: DbSession,
    current_user=Depends(get_current_user),
):
    trip = db.get(Trip, trip_id)

    if trip is None or trip.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found.",
        )

    if trip.status != "active":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Trip has already ended.",
        )

    trip.status = request.status
    trip.ended_at = datetime.utcnow()
    db.commit()
    db.refresh(trip)
    return trip
