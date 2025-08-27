"""Initial database schema

Revision ID: 001
Revises: 
Create Date: 2024-01-01 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create tracks table
    op.create_table('tracks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('artist', sa.String(length=500), nullable=False),
        sa.Column('album', sa.String(length=500), nullable=True),
        sa.Column('year', sa.Integer(), nullable=True),
        sa.Column('genre', sa.String(length=100), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('duration_sec', sa.Float(), nullable=True),
        sa.Column('file_path', sa.String(length=1000), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('bitrate', sa.Integer(), nullable=True),
        sa.Column('sample_rate', sa.Integer(), nullable=True),
        sa.Column('bpm', sa.Float(), nullable=True),
        sa.Column('key', sa.Integer(), nullable=True),
        sa.Column('mode', sa.Integer(), nullable=True),
        sa.Column('energy', sa.Float(), nullable=True),
        sa.Column('danceability', sa.Float(), nullable=True),
        sa.Column('valence', sa.Float(), nullable=True),
        sa.Column('acousticness', sa.Float(), nullable=True),
        sa.Column('instrumentalness', sa.Float(), nullable=True),
        sa.Column('liveness', sa.Float(), nullable=True),
        sa.Column('loudness_db', sa.Float(), nullable=True),
        sa.Column('artwork_url', sa.String(length=1000), nullable=True),
        sa.Column('artwork_embedded', sa.Boolean(), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('isrc', sa.String(length=50), nullable=True),
        sa.Column('recording_mbid', sa.String(length=36), nullable=True),
        sa.Column('release_mbid', sa.String(length=36), nullable=True),
        sa.Column('spotify_id', sa.String(length=100), nullable=True),
        sa.Column('facts', sa.JSON(), nullable=True),
        sa.Column('popularity_score', sa.Float(), nullable=True),
        sa.Column('mood_tags', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_played_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('play_count', sa.Integer(), nullable=False, default=0),
        sa.Column('skip_count', sa.Integer(), nullable=False, default=0),
        sa.Column('last_commentary_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_tracks'))
    )
    op.create_index(op.f('ix_tracks_album'), 'tracks', ['album'], unique=False)
    op.create_index(op.f('ix_tracks_artist'), 'tracks', ['artist'], unique=False)
    op.create_index(op.f('ix_tracks_file_path'), 'tracks', ['file_path'], unique=True)
    op.create_index(op.f('ix_tracks_genre'), 'tracks', ['genre'], unique=False)
    op.create_index(op.f('ix_tracks_id'), 'tracks', ['id'], unique=False)
    op.create_index(op.f('ix_tracks_isrc'), 'tracks', ['isrc'], unique=False)
    op.create_index(op.f('ix_tracks_recording_mbid'), 'tracks', ['recording_mbid'], unique=False)
    op.create_index(op.f('ix_tracks_release_mbid'), 'tracks', ['release_mbid'], unique=False)
    op.create_index(op.f('ix_tracks_spotify_id'), 'tracks', ['spotify_id'], unique=False)
    op.create_index(op.f('ix_tracks_title'), 'tracks', ['title'], unique=False)
    op.create_index(op.f('ix_tracks_year'), 'tracks', ['year'], unique=False)

    # Create plays table
    op.create_table('plays',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('track_id', sa.Integer(), nullable=False),
        sa.Column('liquidsoap_id', sa.String(length=100), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('elapsed_ms', sa.Integer(), nullable=True),
        sa.Column('play_position', sa.Integer(), nullable=True),
        sa.Column('crossfade_duration', sa.Integer(), nullable=True),
        sa.Column('was_skipped', sa.Boolean(), nullable=False, default=False),
        sa.Column('skip_reason', sa.String(length=100), nullable=True),
        sa.Column('triggered_commentary', sa.Boolean(), nullable=False, default=False),
        sa.Column('commentary_before', sa.Boolean(), nullable=False, default=False),
        sa.Column('commentary_after', sa.Boolean(), nullable=False, default=False),
        sa.Column('source_type', sa.String(length=50), nullable=False, default='playlist'),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('client_ip', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['track_id'], ['tracks.id'], name=op.f('fk_plays_track_id_tracks')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_plays'))
    )
    op.create_index(op.f('ix_plays_ended_at'), 'plays', ['ended_at'], unique=False)
    op.create_index(op.f('ix_plays_id'), 'plays', ['id'], unique=False)
    op.create_index(op.f('ix_plays_liquidsoap_id'), 'plays', ['liquidsoap_id'], unique=False)
    op.create_index(op.f('ix_plays_started_at'), 'plays', ['started_at'], unique=False)
    op.create_index(op.f('ix_plays_track_id'), 'plays', ['track_id'], unique=False)

    # Create commentary table
    op.create_table('commentary',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('play_id', sa.Integer(), nullable=True),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('ssml', sa.Text(), nullable=True),
        sa.Column('audio_url', sa.String(length=1000), nullable=True),
        sa.Column('transcript', sa.Text(), nullable=True),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('model', sa.String(length=100), nullable=True),
        sa.Column('voice_provider', sa.String(length=50), nullable=True),
        sa.Column('voice_id', sa.String(length=100), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('generation_time_ms', sa.Integer(), nullable=True),
        sa.Column('tts_time_ms', sa.Integer(), nullable=True),
        sa.Column('context_data', sa.JSON(), nullable=True),
        sa.Column('prompt_template', sa.String(length=100), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('content_flags', sa.JSON(), nullable=True),
        sa.Column('user_rating', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, default='pending'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, default=0),
        sa.Column('broadcasted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('play_count', sa.Integer(), nullable=False, default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('generated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['play_id'], ['plays.id'], name=op.f('fk_commentary_play_id_plays')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_commentary'))
    )
    op.create_index(op.f('ix_commentary_created_at'), 'commentary', ['created_at'], unique=False)
    op.create_index(op.f('ix_commentary_id'), 'commentary', ['id'], unique=False)
    op.create_index(op.f('ix_commentary_play_id'), 'commentary', ['play_id'], unique=False)

    # Create settings table
    op.create_table('settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(length=100), nullable=False),
        sa.Column('value', sa.Text(), nullable=True),
        sa.Column('value_type', sa.String(length=20), nullable=False, default='string'),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_secret', sa.Boolean(), nullable=False, default=False),
        sa.Column('min_value', sa.Float(), nullable=True),
        sa.Column('max_value', sa.Float(), nullable=True),
        sa.Column('allowed_values', sa.JSON(), nullable=True),
        sa.Column('validation_regex', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_by', sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_settings'))
    )
    op.create_index(op.f('ix_settings_category'), 'settings', ['category'], unique=False)
    op.create_index(op.f('ix_settings_id'), 'settings', ['id'], unique=False)
    op.create_index(op.f('ix_settings_key'), 'settings', ['key'], unique=True)

    # Create users table
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=True),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('display_name', sa.String(length=100), nullable=True),
        sa.Column('avatar_url', sa.String(length=1000), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_verified', sa.Boolean(), nullable=False, default=False),
        sa.Column('role', sa.String(length=50), nullable=False, default='listener'),
        sa.Column('permissions', sa.JSON(), nullable=True),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('login_count', sa.Integer(), nullable=False, default=0),
        sa.Column('failed_login_attempts', sa.Integer(), nullable=False, default=0),
        sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('external_id', sa.String(length=255), nullable=True),
        sa.Column('external_provider', sa.String(length=50), nullable=True),
        sa.Column('preferences', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_users'))
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_external_id'), 'users', ['external_id'], unique=False)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_role'), 'users', ['role'], unique=False)


def downgrade() -> None:
    op.drop_table('users')
    op.drop_table('settings')
    op.drop_table('commentary')
    op.drop_table('plays')
    op.drop_table('tracks')