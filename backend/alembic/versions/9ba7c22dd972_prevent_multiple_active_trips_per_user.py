"""prevent multiple active trips per user

Revision ID: 9ba7c22dd972
Revises: 86b84e01fbe0
"""

import sqlalchemy as sa
from alembic import op


revision = "9ba7c22dd972"
down_revision = "86b84e01fbe0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "uq_trips_one_active_per_user",
        "trips",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_trips_one_active_per_user",
        table_name="trips",
    )