
from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class Trip(Base):
    __tablename__ = "trips"

    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'ended')",
            name="ck_trips_status",
        ),
        CheckConstraint(
            "last_latitude IS NULL OR last_latitude BETWEEN -90 AND 90",
            name="ck_trips_latitude",
        ),
        CheckConstraint(
            "last_longitude IS NULL OR last_longitude BETWEEN -180 AND 180",
            name="ck_trips_longitude",
        ),
        CheckConstraint(
            "last_alerted_level IS NULL OR "
            "last_alerted_level IN ('Green', 'Yellow', 'Orange', 'Red')",
            name="ck_trips_last_alerted_level",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )

    route_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        default="active",
        server_default="active",
        nullable=False,
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    last_latitude: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    last_longitude: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    last_location_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    alerted_report_ids: Mapped[list[int]] = mapped_column(
        JSONB,
        default=list,
        server_default="[]",
        nullable=False,
    )

    last_alerted_level: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )
