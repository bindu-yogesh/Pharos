
"""add trip risk alert level

Revision ID: 86b84e01fbe0
Revises: b7c4e2a91f60
"""

from alembic import op
import sqlalchemy as sa


revision = "86b84e01fbe0"
down_revision = "b7c4e2a91f60"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "trips",
        sa.Column("last_alerted_level", sa.String(length=10), nullable=True),
    )
    op.create_check_constraint(
        "ck_trips_last_alerted_level",
        "trips",
        "last_alerted_level IS NULL OR "
        "last_alerted_level IN ('Green', 'Yellow', 'Orange', 'Red')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_trips_last_alerted_level",
        "trips",
        type_="check",
    )
    op.drop_column("trips", "last_alerted_level")
