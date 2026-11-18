from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class NotificationOutbox(Base):
    __tablename__ = "notification_outbox"

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'sent', 'failed')",
            name="ck_notification_outbox_status",
        ),
        Index(
            "ix_notification_outbox_pending",
            "status",
            "next_attempt_at",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    trip_id: Mapped[int] = mapped_column(
        ForeignKey("trips.id"), nullable=False
    )
    dedupe_key: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False
    )
    fcm_token: Mapped[str] = mapped_column(String(500), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="pending", server_default="pending",
        nullable=False,
    )
    attempts: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    next_attempt_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
