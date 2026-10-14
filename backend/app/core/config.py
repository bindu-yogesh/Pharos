
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://pharos_user:pharos_password@localhost:5433/pharos"
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24
    report_expiry_hours: int = 24
    reports_per_hour_limit: int = 5
    clear_votes_threshold: int = 3
    fcm_credentials_path: str | None = None

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
