"""Add track_id FK to commentary table for caching

Revision ID: 009_commentary_track_id
Revises: 008_add_voicing_cache
Create Date: 2026-02-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '009_commentary_track_id'
down_revision: Union[str, None] = '008_add_voicing_cache'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('commentary', sa.Column('track_id', sa.Integer(), nullable=True))
    op.create_index('ix_commentary_track_id', 'commentary', ['track_id'])
    op.create_foreign_key(
        'fk_commentary_track_id_tracks',
        'commentary', 'tracks',
        ['track_id'], ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    op.drop_constraint('fk_commentary_track_id_tracks', 'commentary', type_='foreignkey')
    op.drop_index('ix_commentary_track_id', table_name='commentary')
    op.drop_column('commentary', 'track_id')
