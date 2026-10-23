from datetime import datetime, timedelta, timezone

import bcrypt
from geoalchemy2 import WKTElement
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from backend.app.database import SessionLocal
from backend.app.models.user import User
from backend.app.models.report import Report


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


# Development-only sample points around the Shiradi Ghat corridor.
# These are synthetic test points, not verified historical incident locations.
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


def seed() -> None:
    with SessionLocal() as session:

        # Upsert seed users by their unique email.
        seeded_users = {}

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
                    "preferred_language": statement.excluded.preferred_language,
                },
            )

            session.execute(statement)

        session.flush()

        # Retrieve seeded users.
        for user_data in SEED_USERS:
            user = session.scalar(
                select(User).where(
                    User.email == user_data["email"]
                )
            )

            if user is None:
                raise RuntimeError(
                    f"Failed to create seed user: {user_data['email']}"
                )

            seeded_users[user_data["email"]] = user

        # Use stable descriptions to avoid duplicate sample reports.
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

            # Use one UTC timestamp for both fields.
            now = datetime.now(timezone.utc).replace(tzinfo=None)

            report = Report(
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

            session.add(report)

        session.commit()

    print(
        "Seed complete: 1 admin, 2 drivers, "
        "and up to 5 sample reports."
    )


if __name__ == "__main__":
    seed()