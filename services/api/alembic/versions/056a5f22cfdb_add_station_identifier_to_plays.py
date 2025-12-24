"""add station identifier to plays

Revision ID: 056a5f22cfdb
Revises: 006
Create Date: 2025-10-19 16:01:19.079679

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '056a5f22cfdb'
down_revision: Union[str, None] = '006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('plays', sa.Column('station_identifier', sa.String(length=50), nullable=True))
    op.create_index('ix_plays_station_identifier', 'plays', ['station_identifier'])
    op.execute("UPDATE plays SET station_identifier = 'main' WHERE station_identifier IS NULL")


def downgrade() -> None:
    op.drop_index('ix_plays_station_identifier', table_name='plays')
    op.drop_column('plays', 'station_identifier')
