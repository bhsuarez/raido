"""add identifier to stations

Revision ID: 005
Revises: 004
Create Date: 2025-10-16 21:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add identifier column (nullable initially)
    op.add_column("stations", sa.Column("identifier", sa.String(length=50), nullable=True))

    # Update existing stations to have identifiers based on their names
    # This is a data migration - set identifier for existing stations
    op.execute("UPDATE stations SET identifier = LOWER(REPLACE(name, ' ', '_')) WHERE identifier IS NULL")

    # Make identifier non-nullable and unique
    op.alter_column("stations", "identifier", nullable=False)
    op.create_index(op.f("ix_stations_identifier"), "stations", ["identifier"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_stations_identifier"), table_name="stations")
    op.drop_column("stations", "identifier")
