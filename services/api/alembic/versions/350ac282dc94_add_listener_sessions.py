"""add_listener_sessions

Revision ID: 350ac282dc94
Revises: 009_commentary_track_id
Create Date: 2026-03-15 12:39:27.323971

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '350ac282dc94'
down_revision: Union[str, None] = '009_commentary_track_id'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create listener_sessions table
    op.create_table('listener_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('station', sa.String(length=100), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_heartbeat_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('region', sa.String(length=100), nullable=True),
        sa.Column('country', sa.String(length=100), nullable=True),
        sa.Column('country_code', sa.String(length=2), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('browser', sa.String(length=100), nullable=True),
        sa.Column('os', sa.String(length=100), nullable=True),
        sa.Column('device_type', sa.String(length=20), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_listener_sessions_user_id_users')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_listener_sessions')),
    )
    op.create_index(op.f('ix_listener_sessions_id'), 'listener_sessions', ['id'], unique=False)
    op.create_index(op.f('ix_listener_sessions_user_id'), 'listener_sessions', ['user_id'], unique=False)
    op.create_index(op.f('ix_listener_sessions_ended_at'), 'listener_sessions', ['ended_at'], unique=False)
    # Schema cleanup: drop deprecated columns and constraints
    op.drop_constraint('fk_commentary_track_id_tracks', 'commentary', type_='foreignkey')
    op.create_foreign_key(op.f('fk_commentary_track_id_tracks'), 'commentary', 'tracks', ['track_id'], ['id'])
    op.create_index(op.f('ix_settings_key'), 'settings', ['key'], unique=False)
    op.drop_index('ix_stations_name', table_name='stations')
    op.drop_index('ix_stations_slug', table_name='stations')
    op.drop_constraint('uq_stations_slug', 'stations', type_='unique')
    op.drop_constraint('uq_stations_stream_mount', 'stations', type_='unique')
    op.drop_column('stations', 'slug')
    op.drop_column('stations', 'stream_name')
    op.drop_column('stations', 'stream_mount')
    op.drop_column('tracks', 'is_christmas')


def downgrade() -> None:
    op.add_column('tracks', sa.Column('is_christmas', sa.BOOLEAN(), server_default=sa.text('false'), autoincrement=False, nullable=False))
    op.add_column('stations', sa.Column('stream_mount', sa.VARCHAR(length=200), autoincrement=False, nullable=False))
    op.add_column('stations', sa.Column('stream_name', sa.VARCHAR(length=200), autoincrement=False, nullable=True))
    op.add_column('stations', sa.Column('slug', sa.VARCHAR(length=100), autoincrement=False, nullable=False))
    op.create_unique_constraint('uq_stations_stream_mount', 'stations', ['stream_mount'])
    op.create_unique_constraint('uq_stations_slug', 'stations', ['slug'])
    op.create_index('ix_stations_slug', 'stations', ['slug'], unique=False)
    op.create_index('ix_stations_name', 'stations', ['name'], unique=False)
    op.drop_index(op.f('ix_settings_key'), table_name='settings')
    op.drop_constraint(op.f('fk_commentary_track_id_tracks'), 'commentary', type_='foreignkey')
    op.create_foreign_key('fk_commentary_track_id_tracks', 'commentary', 'tracks', ['track_id'], ['id'], ondelete='SET NULL')
    op.drop_index(op.f('ix_listener_sessions_ended_at'), table_name='listener_sessions')
    op.drop_index(op.f('ix_listener_sessions_user_id'), table_name='listener_sessions')
    op.drop_index(op.f('ix_listener_sessions_id'), table_name='listener_sessions')
    op.drop_table('listener_sessions')