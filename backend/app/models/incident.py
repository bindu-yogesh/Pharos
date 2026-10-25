from datetime import date

from geoalchemy2 import Geometry
from sqlalchemy import CheckConstraint, Date, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class IncidentHistory(Base):
    __tablename__ = "incidents_history"

    __table_args__ = (
        CheckConstraint(
            "location_confidence IN ('exact', 'approximate', 'unknown')",
            name="ck_incidents_history_location_confidence",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_id: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
    )
    incident_date: Mapped[date] = mapped_column(Date, nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    location_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    geom = mapped_column(
        Geometry(geometry_type="POINT", srid=4326),
        nullable=True,
    )
    location_confidence: Mapped[str] = mapped_column(
        String(20),
        default="unknown",
        nullable=False,
    )
    source: Mapped[str] = mapped_column(String(500), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
