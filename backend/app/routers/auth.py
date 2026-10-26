from ..schemas.auth import ProfileUpdateRequest
from ..security.deps import get_current_user
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from ..security.jwt import create_token
from ..security.passwords import hash_password, verify_password


router = APIRouter(prefix="/auth", tags=["Authentication"])
profile_router = APIRouter(tags=["User Profile"])

DbSession = Annotated[Session, Depends(get_db)]


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    request: RegisterRequest,
    db: DbSession,
) -> User:
    """Register a new driver account."""
    existing_user = db.scalar(
        select(User).where(User.email == str(request.email))
    )

    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        )

    user = User(
        name=request.name,
        email=str(request.email),
        password_hash=hash_password(request.password),
        role="driver",
        preferred_language=request.preferred_language,
    )

    db.add(user)
    try:
        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()
        raise

    return user


@router.post("/login", response_model=TokenResponse)
def login(
    request: LoginRequest,
    db: DbSession,
) -> TokenResponse:
    """Authenticate a user and return a JWT access token."""
    user = db.scalar(
        select(User).where(User.email == str(request.email))
    )

    if user is None or not verify_password(
        request.password,
        user.password_hash if user is not None else "",
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.is_blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is blocked",
        )

    return TokenResponse(
        access_token=create_token(user.id, user.role),
        token_type="bearer",
    )

@profile_router.put("/user/profile", response_model=UserResponse)
def update_profile(
    request: ProfileUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: DbSession,
) -> User:
    """Update the authenticated user's name and preferred language."""
    current_user.name = request.name
    current_user.preferred_language = request.preferred_language
    db.commit()
    db.refresh(current_user)
    return current_user
