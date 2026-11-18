"""add transactional notification outbox

Revision ID: b7c42a91d603
Revises: 9ba7c22dd972
"""

from alembic import op
import sqlalchemy as sa


revision = "b7c42a91d603"
down_revision = "9ba7c22dd972"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notification_outbox",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id", sa.Integer(),
            sa.ForeignKey("users.id"), nullable=False,
        ),
        sa.Column(
            "trip_id", sa.Integer(),
            sa.ForeignKey("trips.id"), nullable=False,
        ),
        sa.Column("dedupe_key", sa.String(255), nullable=False, unique=True),
        sa.Column("fcm_token", sa.String(500), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "status", sa.String(20),
            nullable=False, server_default="pending",
        ),
        sa.Column(
            "attempts", sa.Integer(),
            nullable=False, server_default="0",
        ),
        sa.Column("next_attempt_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending', 'sent', 'failed')",
            name="ck_notification_outbox_status",
        ),
    )
    op.create_index(
        "ix_notification_outbox_pending",
        "notification_outbox",
        ["status", "next_attempt_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_notification_outbox_pending",
        table_name="notification_outbox",
    )
    op.drop_table("notification_outbox")
