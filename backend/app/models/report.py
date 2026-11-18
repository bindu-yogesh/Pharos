
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class Report(Base):
    __tablename__ = "reports"

    __table_args__ = (
        CheckConstraint(
            "type IN ('landslide', 'falling_rock', 'blockage')",
            name="ck_reports_type",
        ),
        CheckConstraint(
            "severity BETWEEN 1 AND 3",
            name="ck_reports_severity",
        ),
        CheckConstraint(
            "status IN ('active', 'cleared', 'rejected')",
            name="ck_reports_status",
        ),
        Index("ix_reports_expires_at", "expires_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    photo_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    geom = mapped_column(
        Geometry(geometry_type="POINT", srid=4326),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    user = relationship("User", back_populates="reports")
