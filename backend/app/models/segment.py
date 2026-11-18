from geoalchemy2 import Geometry
from sqlalchemy import Float, Integer
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class RoadSegment(Base):
    __tablename__ = "road_segments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    segment_no: Mapped[int] = mapped_column(
        Integer,
        unique=True,
        nullable=False,
    )

    geom = mapped_column(
        Geometry(geometry_type="LINESTRING", srid=4326),
        nullable=False,
    )

    length_m: Mapped[float] = mapped_column(Float, nullable=False)

    elevation_start_m: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    elevation_end_m: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    slope_percent: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )