import os
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import bcrypt
from geoalchemy2 import WKTElement
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from backend.app.core.config import settings
from backend.app.database import SessionLocal
from backend.app.models.report import Report
from backend.app.models.user import User


SEED_USERS = [
    {
        "name": "Pharos Admin",
        "email": "admin.seed@pharos.local",
        "password": "ChangeMe_Admin_2026!",
        "role": "admin",
    },
    {
        "name": "Sample Driver One",
        "email": "driver1.seed@pharos.local",
        "password": "ChangeMe_Driver1_2026!",
        "role": "driver",
    },
    {
        "name": "Sample Driver Two",
        "email": "driver2.seed@pharos.local",
        "password": "ChangeMe_Driver2_2026!",
        "role": "driver",
    },
]


# Synthetic development/test data only.
# These are NOT verified historical incident locations.
SEED_REPORTS = [
    {
        "type": "landslide",
        "severity": 3,
        "description": "[PHAROS SEED] Sample landslide report 1",
        "longitude": 75.63,
        "latitude": 12.84,
    },
    {
        "type": "falling_rock",
        "severity": 2,
        "description": "[PHAROS SEED] Sample falling-rock report 2",
        "longitude": 75.65,
        "latitude": 12.85,
    },
    {
        "type": "blockage",
        "severity": 3,
        "description": "[PHAROS SEED] Sample blockage report 3",
        "longitude": 75.67,
        "latitude": 12.86,
    },
    {
        "type": "landslide",
        "severity": 2,
        "description": "[PHAROS SEED] Sample landslide report 4",
        "longitude": 75.69,
        "latitude": 12.87,
    },
    {
        "type": "falling_rock",
        "severity": 1,
        "description": "[PHAROS SEED] Sample falling-rock report 5",
        "longitude": 75.71,
        "latitude": 12.88,
    },
]


def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def validate_development_database() -> None:
    """Fail closed unless configured for the expected local demo database."""
    if os.getenv("PHAROS_ENV", "").lower() != "development":
        raise RuntimeError(
            "Seed script is development-only. "
            "Set PHAROS_ENV=development to run it."
        )

    database_url = urlparse(settings.database_url)

    if (
        database_url.scheme != "postgresql+psycopg"
        or database_url.hostname not in {"localhost", "127.0.0.1"}
        or database_url.port != 5433
        or database_url.path != "/pharos"
        or database_url.username != "pharos_user"
    ):
        raise RuntimeError(
            "Seeding blocked: database URL is not the expected "
            "local Pharos development database."
        )


def seed() -> None:
    with SessionLocal() as session:
        seeded_users = {}

        # Upsert development users by unique email.
        for user_data in SEED_USERS:
            values = {
                "name": user_data["name"],
                "email": user_data["email"],
                "password_hash": hash_password(user_data["password"]),
                "role": user_data["role"],
                "preferred_language": "en",
                "is_blocked": False,
                "trust_score": 0.0,
            }

            statement = insert(User).values(**values)
            statement = statement.on_conflict_do_update(
                index_elements=[User.email],
                set_={
                    "name": statement.excluded.name,
                    "role": statement.excluded.role,
                    "preferred_language": (
                        statement.excluded.preferred_language
                    ),
                },
            )
            session.execute(statement)

        session.flush()

        for user_data in SEED_USERS:
            user = session.scalar(
                select(User).where(User.email == user_data["email"])
            )
            if user is None:
                raise RuntimeError(
                    f"Failed to retrieve seed user: {user_data['email']}"
                )
            seeded_users[user_data["email"]] = user

        driver_emails = [
            "driver1.seed@pharos.local",
            "driver2.seed@pharos.local",
        ]

        for index, report_data in enumerate(SEED_REPORTS):
            existing = session.scalar(
                select(Report).where(
                    Report.description == report_data["description"]
                )
            )
            if existing is not None:
                continue

            driver = seeded_users[
                driver_emails[index % len(driver_emails)]
            ]
            now = datetime.now(timezone.utc).replace(tzinfo=None)

            session.add(
                Report(
                    user_id=driver.id,
                    type=report_data["type"],
                    severity=report_data["severity"],
                    description=report_data["description"],
                    geom=WKTElement(
                        f"POINT({report_data['longitude']} "
                        f"{report_data['latitude']})",
                        srid=4326,
                    ),
                    status="active",
                    created_at=now,
                    expires_at=now + timedelta(hours=24),
                )
            )

        session.commit()

    print("Development seed complete: 3 users and up to 5 sample reports.")


if __name__ == "__main__":
    validate_development_database()
    seed()
