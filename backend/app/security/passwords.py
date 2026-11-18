import bcrypt


BCRYPT_MAX_PASSWORD_BYTES = 72


def _password_bytes(password: str) -> bytes:
    """Encode a password and enforce bcrypt's 72-byte limit."""
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > BCRYPT_MAX_PASSWORD_BYTES:
        raise ValueError("Password must not exceed 72 UTF-8 bytes")
    return password_bytes


def hash_password(password: str) -> str:
    """Hash a password using bcrypt without silently truncating it."""
    hashed = bcrypt.hashpw(_password_bytes(password), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Safely verify a password against a stored bcrypt hash."""
    try:
        return bcrypt.checkpw(
            _password_bytes(password),
            password_hash.encode("utf-8"),
        )
    except (ValueError, TypeError, UnicodeError):
        return False
