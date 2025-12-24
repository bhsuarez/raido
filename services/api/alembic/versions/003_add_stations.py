"""add stations tables

Revision ID: 003
Revises: 002
Create Date: 2024-01-01 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "stations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("genre", sa.String(length=100), nullable=True),
        sa.Column("dj_persona", sa.String(length=100), nullable=True),
        sa.Column("artwork_url", sa.String(length=1000), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_stations")),
    )
    op.create_index(op.f("ix_stations_id"), "stations", ["id"], unique=False)
    op.create_index(op.f("ix_stations_name"), "stations", ["name"], unique=True)
    op.create_index(op.f("ix_stations_genre"), "stations", ["genre"], unique=False)

    op.create_table(
        "station_tracks",
        sa.Column("station_id", sa.Integer(), nullable=False),
        sa.Column("track_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["station_id"],
            ["stations.id"],
            name=op.f("fk_station_tracks_station_id_stations"),
        ),
        sa.ForeignKeyConstraint(
            ["track_id"], ["tracks.id"], name=op.f("fk_station_tracks_track_id_tracks")
        ),
        sa.PrimaryKeyConstraint(
            "station_id", "track_id", name=op.f("pk_station_tracks")
        ),
    )


def downgrade() -> None:
    op.drop_table("station_tracks")
    op.drop_index(op.f("ix_stations_genre"), table_name="stations")
    op.drop_index(op.f("ix_stations_name"), table_name="stations")
    op.drop_index(op.f("ix_stations_id"), table_name="stations")
    op.drop_table("stations")
