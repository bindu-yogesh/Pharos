from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "b7c4e2a91f60"
down_revision: Union[str, Sequence[str], None] = "d8e59076e620"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "trips",
        sa.Column("last_latitude", sa.Float(), nullable=True),
    )

    op.add_column(
        "trips",
        sa.Column("last_longitude", sa.Float(), nullable=True),
    )

    op.add_column(
        "trips",
        sa.Column("last_location_at", sa.DateTime(), nullable=True),
    )

    op.add_column(
        "trips",
        sa.Column(
            "alerted_report_ids",
            postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )

    op.create_check_constraint(
        "ck_trips_latitude",
        "trips",
        "last_latitude IS NULL OR last_latitude BETWEEN -90 AND 90",
    )

    op.create_check_constraint(
        "ck_trips_longitude",
        "trips",
        "last_longitude IS NULL OR last_longitude BETWEEN -180 AND 180",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_trips_longitude",
        "trips",
        type_="check",
    )

    op.drop_constraint(
        "ck_trips_latitude",
        "trips",
        type_="check",
    )

    op.drop_column("trips", "alerted_report_ids")
    op.drop_column("trips", "last_location_at")
    op.drop_column("trips", "last_longitude")
    op.drop_column("trips", "last_latitude")