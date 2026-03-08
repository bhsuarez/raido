"""Add TTS worker control fields to voicing_worker_config

Revision ID: 010_add_tts_worker_config
Revises: 009_commentary_track_id
Create Date: 2026-03-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '010_add_tts_worker_config'
down_revision: Union[str, None] = '009_commentary_track_id'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'voicing_worker_config',
        sa.Column('tts_is_running', sa.Boolean(), nullable=False, server_default='false'),
    )
    op.add_column(
        'voicing_worker_config',
        sa.Column('tts_last_processed_track_id', sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('voicing_worker_config', 'tts_last_processed_track_id')
    op.drop_column('voicing_worker_config', 'tts_is_running')
