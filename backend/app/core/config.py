from urllib.parse import urlsplit

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = (
        "postgresql+psycopg://pharos_user:pharos_password@localhost:5433/pharos"
    )
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24
    report_expiry_hours: int = 24
    reports_per_hour_limit: int = 5
    clear_votes_threshold: int = 3
    fcm_credentials_path: str | None = None
    osrm_base_url: str = "https://router.project-osrm.org"

    model_config = SettingsConfigDict(env_file=".env")


    @field_validator("osrm_base_url")
    @classmethod
    def validate_osrm_base_url(cls, value: str) -> str:
        value = value.strip().rstrip("/")
        parsed = urlsplit(value)

        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("OSRM_BASE_URL must be a valid HTTP or HTTPS URL")

        return value

    @field_validator("jwt_secret")
    @classmethod
    def validate_jwt_secret(cls, value: str) -> str:
        value = value.strip()

        placeholders = {
            "change-me",
            "changeme",
            "replace-with-a-long-random-secret",
            "your-secret",
            "secret",
        }

        if value.lower() in placeholders:
            raise ValueError("JWT_SECRET must not use a placeholder value")

        if len(value.encode("utf-8")) < 32:
            raise ValueError("JWT_SECRET must be at least 32 bytes long")

        return value

    @field_validator("jwt_algorithm")
    @classmethod
    def validate_jwt_algorithm(cls, value: str) -> str:
        value = value.strip().upper()

        if value != "HS256":
            raise ValueError("Only HS256 is supported for JWT signing")

        return value

    @field_validator("jwt_expire_minutes")
    @classmethod
    def validate_jwt_expiry(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("JWT expiration must be greater than zero")

        return value


settings = Settings()
