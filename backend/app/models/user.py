
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class User(Base):
    __tablename__ = "users"

    __table_args__ = (
        CheckConstraint(
            "role IN ('driver', 'admin')",
            name="ck_users_role",
        ),
        CheckConstraint(
            "preferred_language IN ('en', 'hi', 'kn')",
            name="ck_users_preferred_language",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(
        String(150),
        unique=True,
        index=True,
        nullable=False,
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(
        String(20),
        default="driver",
        server_default="driver",
        nullable=False,
    )
    preferred_language: Mapped[str] = mapped_column(
        String(2),
        default="en",
        server_default="en",
        nullable=False,
    )
    is_blocked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )
    trust_score: Mapped[float | None] = mapped_column(
        Float,
        default=0.0,
        nullable=True,
    )

    reports = relationship("Report", back_populates="user")
