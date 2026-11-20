from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.device import DeviceToken
from ..schemas.device import DeviceRegisterRequest, DeviceResponse
from ..security.deps import get_current_user

router = APIRouter(prefix="/devices", tags=["devices"])

DbSession = Annotated[Session, Depends(get_db)]


@router.post(
    "",
    response_model=DeviceResponse,
    status_code=status.HTTP_200_OK,
)
def register_device(
    request: DeviceRegisterRequest,
    db: DbSession,
    current_user=Depends(get_current_user),
):
    """Register an FCM registration token for the authenticated user."""

    device = db.scalar(
        select(DeviceToken).where(
            DeviceToken.fcm_token == request.token
        )
    )

    if device is None:
        device = DeviceToken(
            user_id=current_user.id,
            fcm_token=request.token,
        )
        db.add(device)
    else:
        device.user_id = current_user.id

    db.commit()

    return {"message": "Device registered successfully."}