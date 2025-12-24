"""add station timestamps and is_active

Revision ID: 006
Revises: 005
Create Date: 2025-10-16 21:10:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from datetime import datetime, timezone

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add columns (nullable initially to allow setting defaults)
    op.add_column("stations", sa.Column("is_active", sa.Boolean(), nullable=True))
    op.add_column("stations", sa.Column("created_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("stations", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))

    # Set defaults for existing rows
    now = datetime.now(timezone.utc)
    op.execute(f"UPDATE stations SET is_active = true WHERE is_active IS NULL")
    op.execute(f"UPDATE stations SET created_at = '{now.isoformat()}' WHERE created_at IS NULL")
    op.execute(f"UPDATE stations SET updated_at = '{now.isoformat()}' WHERE updated_at IS NULL")

    # Make columns non-nullable
    op.alter_column("stations", "is_active", nullable=False)
    op.alter_column("stations", "created_at", nullable=False)
    op.alter_column("stations", "updated_at", nullable=False)


def downgrade() -> None:
    op.drop_column("stations", "updated_at")
    op.drop_column("stations", "created_at")
    op.drop_column("stations", "is_active")
