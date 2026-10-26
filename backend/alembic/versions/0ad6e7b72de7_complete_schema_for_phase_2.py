
"""complete schema for phase 2

Revision ID: 0ad6e7b72de7
Revises: 9c179d931b91
Create Date: 2026-10-14 19:25:36.412660

"""
from typing import Sequence, Union

import geoalchemy2
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0ad6e7b72de7"
down_revision: Union[str, Sequence[str], None] = "9c179d931b91"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "incidents_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("external_id", sa.String(length=50), nullable=False),
        sa.Column("incident_date", sa.Date(), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("location_name", sa.String(length=200), nullable=False),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(
                geometry_type="POINT",
                srid=4326,
                dimension=2,
                from_text="ST_GeomFromEWKT",
                name="geometry",
            ),
            nullable=True,
        ),
        sa.Column("location_confidence", sa.String(length=20), nullable=False),
        sa.Column("source", sa.String(length=500), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_id"),
    )

    op.create_table(
        "road_segments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("segment_no", sa.Integer(), nullable=False),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(
                geometry_type="LINESTRING",
                srid=4326,
                dimension=2,
                from_text="ST_GeomFromEWKT",
                name="geometry",
            ),
            nullable=False,
        ),
        sa.Column("length_m", sa.Float(), nullable=False),
        sa.Column("elevation_start_m", sa.Float(), nullable=False),
        sa.Column("elevation_end_m", sa.Float(), nullable=False),
        sa.Column("slope_percent", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("segment_no"),
    )

    op.create_table(
        "device_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("fcm_token", sa.String(length=500), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("fcm_token"),
    )

    op.create_table(
        "trips",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "route_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(),
            server_default="active",
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "status IN ('active', 'ended')",
            name="ck_trips_status",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "report_votes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("report_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("vote", sa.String(length=10), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "vote IN ('confirm', 'clear')",
            name="ck_report_votes_vote",
        ),
        sa.ForeignKeyConstraint(
            ["report_id"],
            ["reports.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "report_id",
            "user_id",
            name="uq_report_votes_report_user",
        ),
    )

    op.create_index(
        "ix_reports_expires_at",
        "reports",
        ["expires_at"],
        unique=False,
    )

    op.create_check_constraint(
        "ck_reports_type",
        "reports",
        "type IN ('landslide', 'falling_rock', 'blockage')",
    )
    op.create_check_constraint(
        "ck_reports_severity",
        "reports",
        "severity BETWEEN 1 AND 3",
    )
    op.create_check_constraint(
        "ck_reports_status",
        "reports",
        "status IN ('active', 'cleared', 'rejected')",
    )

    op.add_column(
        "users",
        sa.Column("password_hash", sa.String(length=255), nullable=False),
    )
    op.add_column(
        "users",
        sa.Column(
            "role",
            sa.String(length=20),
            server_default="driver",
            nullable=False,
        ),
    )
    op.alter_column(
        "users",
        "language",
        new_column_name="preferred_language",
        existing_type=sa.String(length=20),
        type_=sa.String(length=2),
    )
    op.add_column(
        "users",
        sa.Column(
            "is_blocked",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
    )
    op.alter_column(
        "users",
        "trust_score",
        existing_type=sa.DOUBLE_PRECISION(precision=53),
        nullable=True,
    )
    op.drop_constraint(op.f("users_email_key"), "users", type_="unique")
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_check_constraint(
        "ck_users_role",
        "users",
        "role IN ('driver', 'admin')",
    )
    op.create_check_constraint(
        "ck_users_preferred_language",
        "users",
        "preferred_language IN ('en', 'hi', 'kn')",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.create_unique_constraint(
        op.f("users_email_key"),
        "users",
        ["email"],
        postgresql_nulls_not_distinct=False,
    )
    op.alter_column(
        "users",
        "trust_score",
        existing_type=sa.DOUBLE_PRECISION(precision=53),
        nullable=False,
    )

    op.drop_constraint("ck_reports_status", "reports", type_="check")
    op.drop_constraint("ck_reports_severity", "reports", type_="check")
    op.drop_constraint("ck_reports_type", "reports", type_="check")
    op.drop_constraint("ck_users_preferred_language", "users", type_="check")
    op.drop_constraint("ck_users_role", "users", type_="check")

    op.drop_column("users", "is_blocked")
    op.alter_column(
        "users",
        "preferred_language",
        new_column_name="language",
        existing_type=sa.String(length=2),
        type_=sa.String(length=20),
    )
    op.drop_column("users", "role")
    op.drop_column("users", "password_hash")

    op.drop_index("ix_reports_expires_at", table_name="reports")
    op.drop_table("report_votes")
    op.drop_table("trips")
    op.drop_table("device_tokens")

    op.drop_index(
        "idx_road_segments_geom",
        table_name="road_segments",
        postgresql_using="gist",
    )
    op.drop_table("road_segments")

    op.drop_index(
        "idx_incidents_history_geom",
        table_name="incidents_history",
        postgresql_using="gist",
    )
    op.drop_table("incidents_history")
