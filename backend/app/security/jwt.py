
from datetime import datetime, timedelta, timezone

import jwt

from ..core.config import settings


def create_token(user_id: int, role: str) -> str:
    """Create a signed JWT containing the user ID, role, and expiry."""
    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }

    return jwt.encode(
        payload,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def decode_token(token: str) -> dict:
    """Decode a JWT, rejecting expired tokens and invalid signatures."""
    return jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
    )
