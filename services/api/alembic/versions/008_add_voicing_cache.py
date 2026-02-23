"""Add voicing cache tables for pre-rendered commentary engine

Revision ID: 008_add_voicing_cache
Revises: 007_elapsed_ms_bigint
Create Date: 2026-02-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '008_add_voicing_cache'
down_revision: Union[str, None] = '007_elapsed_ms_bigint'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Per-track cached script + audio
    op.create_table(
        'track_voicing_cache',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('track_id', sa.Integer(), nullable=False),
        sa.Column('genre_persona', sa.String(length=100), nullable=True),
        sa.Column('script_text', sa.Text(), nullable=True),
        sa.Column('audio_filename', sa.String(length=500), nullable=True),
        sa.Column('audio_duration_sec', sa.Float(), nullable=True),
        sa.Column('provider', sa.String(length=50), nullable=True),
        sa.Column('model', sa.String(length=100), nullable=True),
        sa.Column('voice_provider', sa.String(length=50), nullable=True),
        sa.Column('voice_id', sa.String(length=100), nullable=True),
        sa.Column('input_tokens', sa.Integer(), nullable=True),
        sa.Column('output_tokens', sa.Integer(), nullable=True),
        sa.Column('estimated_cost_usd', sa.Float(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['track_id'], ['tracks.id'], name=op.f('fk_track_voicing_cache_track_id_tracks'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_track_voicing_cache')),
        sa.UniqueConstraint('track_id', name=op.f('uq_track_voicing_cache_track_id')),
    )
    op.create_index(op.f('ix_track_voicing_cache_id'), 'track_voicing_cache', ['id'], unique=False)
    op.create_index(op.f('ix_track_voicing_cache_track_id'), 'track_voicing_cache', ['track_id'], unique=True)
    op.create_index(op.f('ix_track_voicing_cache_status'), 'track_voicing_cache', ['status'], unique=False)

    # Daily budget tracking
    op.create_table(
        'voicing_budget',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('total_input_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_output_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_cost_usd', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('requests_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_voicing_budget')),
        sa.UniqueConstraint('date', name=op.f('uq_voicing_budget_date')),
    )
    op.create_index(op.f('ix_voicing_budget_id'), 'voicing_budget', ['id'], unique=False)
    op.create_index(op.f('ix_voicing_budget_date'), 'voicing_budget', ['date'], unique=True)

    # Singleton worker config/status
    op.create_table(
        'voicing_worker_config',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('is_running', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('dry_run_mode', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('daily_spend_limit_usd', sa.Float(), nullable=False, server_default='1.00'),
        sa.Column('total_project_limit_usd', sa.Float(), nullable=False, server_default='10.00'),
        sa.Column('rate_limit_per_minute', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('total_tracks_estimated', sa.Integer(), nullable=True),
        sa.Column('voiced_tracks_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_spent_usd', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('last_processed_track_id', sa.Integer(), nullable=True),
        sa.Column('paused_reason', sa.Text(), nullable=True),
        sa.Column('dry_run_projected_cost_usd', sa.Float(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_voicing_worker_config')),
    )
    op.create_index(op.f('ix_voicing_worker_config_id'), 'voicing_worker_config', ['id'], unique=False)

    # Insert default singleton config row
    op.execute(
        "INSERT INTO voicing_worker_config (id, is_running, dry_run_mode, daily_spend_limit_usd, "
        "total_project_limit_usd, rate_limit_per_minute, voiced_tracks_count, total_spent_usd) "
        "VALUES (1, false, false, 1.00, 10.00, 10, 0, 0.0)"
    )


def downgrade() -> None:
    op.drop_table('voicing_worker_config')
    op.drop_index(op.f('ix_voicing_budget_date'), table_name='voicing_budget')
    op.drop_index(op.f('ix_voicing_budget_id'), table_name='voicing_budget')
    op.drop_table('voicing_budget')
    op.drop_index(op.f('ix_track_voicing_cache_status'), table_name='track_voicing_cache')
    op.drop_index(op.f('ix_track_voicing_cache_track_id'), table_name='track_voicing_cache')
    op.drop_index(op.f('ix_track_voicing_cache_id'), table_name='track_voicing_cache')
    op.drop_table('track_voicing_cache')
