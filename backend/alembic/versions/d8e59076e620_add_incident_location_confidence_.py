"""add incident location confidence constraint

Revision ID: d8e59076e620
Revises: 0ad6e7b72de7
Create Date: 2026-10-23 05:23:25.536984

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd8e59076e620'
down_revision: Union[str, Sequence[str], None] = '0ad6e7b72de7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade() -> None:
    op.create_check_constraint(
        "ck_incidents_history_location_confidence",
        "incidents_history",
        "location_confidence IN ('exact', 'approximate', 'unknown')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_incidents_history_location_confidence",
        "incidents_history",
        type_="check",
    )
