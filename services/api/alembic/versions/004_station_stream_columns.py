"""add stream metadata to stations

Revision ID: 004_station_stream_columns
Revises: 003
Create Date: 2024-12-01 00:00:00.000000
"""

from typing import Sequence, Union
import re

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column

revision: str = "004_station_stream_columns"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _slugify(value: str, fallback: str) -> str:
    """Return a filesystem-safe slug for an existing station name."""
    if not value:
        return fallback
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or fallback


def upgrade() -> None:
    op.add_column("stations", sa.Column("slug", sa.String(length=100), nullable=True))
    op.add_column(
        "stations", sa.Column("stream_mount", sa.String(length=200), nullable=True)
    )
    op.add_column(
        "stations", sa.Column("stream_name", sa.String(length=200), nullable=True)
    )
    op.create_index(op.f("ix_stations_slug"), "stations", ["slug"], unique=True)
    op.create_index(
        op.f("ix_stations_stream_mount"), "stations", ["stream_mount"], unique=True
    )

    station_table = table(
        "stations",
        column("id", sa.Integer()),
        column("name", sa.String()),
        column("slug", sa.String()),
        column("stream_mount", sa.String()),
        column("stream_name", sa.String()),
    )

    bind = op.get_bind()
    rows = bind.execute(sa.select(station_table.c.id, station_table.c.name)).fetchall()

    for station_id, name in rows:
        fallback_slug = f"station-{station_id}"
        slug = _slugify(name, fallback_slug)
        mount = f"/{slug}.mp3"
        stream_display_name = name or f"Raido Station {station_id}"
        bind.execute(
            station_table.update()
            .where(station_table.c.id == station_id)
            .values(slug=slug, stream_mount=mount, stream_name=stream_display_name)
        )

    op.alter_column("stations", "slug", nullable=False)
    op.alter_column("stations", "stream_mount", nullable=False)


def downgrade() -> None:
    op.alter_column("stations", "stream_mount", nullable=True)
    op.alter_column("stations", "slug", nullable=True)
    op.drop_index(op.f("ix_stations_stream_mount"), table_name="stations")
    op.drop_index(op.f("ix_stations_slug"), table_name="stations")
    op.drop_column("stations", "stream_name")
    op.drop_column("stations", "stream_mount")
    op.drop_column("stations", "slug")
