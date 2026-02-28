"""Add default settings

Revision ID: 002
Revises: 001
Create Date: 2024-01-01 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Insert default settings
    settings_table = sa.table('settings',
        sa.column('key', sa.String),
        sa.column('value', sa.String),
        sa.column('value_type', sa.String),
        sa.column('category', sa.String),
        sa.column('description', sa.String),
        sa.column('is_secret', sa.Boolean)
    )
    
    op.bulk_insert(settings_table, [
        # DJ Configuration
        {
            'key': 'dj_commentary_interval',
            'value': '1',
            'value_type': 'int',
            'category': 'dj',
            'description': 'Number of songs between DJ commentary (1 = after every song)',
            'is_secret': False
        },
        {
            'key': 'dj_max_seconds',
            'value': '30',
            'value_type': 'int',
            'category': 'dj',
            'description': 'Maximum duration for DJ commentary in seconds',
            'is_secret': False
        },
        {
            'key': 'dj_tone',
            'value': 'energetic',
            'value_type': 'string',
            'category': 'dj',
            'description': 'DJ personality tone (energetic, chill, professional, etc.)',
            'is_secret': False
        },
        {
            'key': 'dj_provider',
            'value': 'ollama',
            'value_type': 'string',
            'category': 'dj',
            'description': 'AI provider for DJ commentary (ollama, templates, disabled)',
            'is_secret': False
        },
        {
            'key': 'dj_voice_provider',
            'value': 'kokoro',
            'value_type': 'string',
            'category': 'dj',
            'description': 'TTS provider (kokoro, liquidsoap, chatterbox)',
            'is_secret': False
        },
        {
            'key': 'dj_profanity_filter',
            'value': 'true',
            'value_type': 'bool',
            'category': 'dj',
            'description': 'Enable profanity filtering for DJ commentary',
            'is_secret': False
        },
        {
            'key': 'station_name',
            'value': 'Raido Pirate Radio',
            'value_type': 'string',
            'category': 'station',
            'description': 'Name of the radio station',
            'is_secret': False
        },
        
        # Stream Configuration
        {
            'key': 'stream_bitrate',
            'value': '128',
            'value_type': 'int',
            'category': 'stream',
            'description': 'Stream bitrate in kbps',
            'is_secret': False
        },
        {
            'key': 'stream_format',
            'value': 'mp3',
            'value_type': 'string',
            'category': 'stream',
            'description': 'Stream audio format',
            'is_secret': False
        },
        {
            'key': 'crossfade_duration',
            'value': '2.0',
            'value_type': 'float',
            'category': 'stream',
            'description': 'Crossfade duration between tracks in seconds',
            'is_secret': False
        },
        
        # UI Configuration
        {
            'key': 'ui_theme',
            'value': 'dark',
            'value_type': 'string',
            'category': 'ui',
            'description': 'Default UI theme (dark, light)',
            'is_secret': False
        },
        {
            'key': 'ui_show_artwork',
            'value': 'true',
            'value_type': 'bool',
            'category': 'ui',
            'description': 'Show album artwork in the player',
            'is_secret': False
        },
        {
            'key': 'ui_history_limit',
            'value': '50',
            'value_type': 'int',
            'category': 'ui',
            'description': 'Maximum number of tracks to show in history',
            'is_secret': False
        },
        
        # Features
        {
            'key': 'enable_commentary',
            'value': 'true',
            'value_type': 'bool',
            'category': 'features',
            'description': 'Enable AI DJ commentary generation',
            'is_secret': False
        },
        {
            'key': 'enable_track_enrichment',
            'value': 'true',
            'value_type': 'bool',
            'category': 'features',
            'description': 'Enable automatic track metadata enrichment',
            'is_secret': False
        },
        {
            'key': 'enable_artwork_lookup',
            'value': 'true',
            'value_type': 'bool',
            'category': 'features',
            'description': 'Enable automatic album artwork lookup',
            'is_secret': False
        }
    ])


def downgrade() -> None:
    # Remove default settings
    op.execute(
        "DELETE FROM settings WHERE key IN ("
        "'dj_commentary_interval', 'dj_max_seconds', 'dj_tone', "
        "'dj_provider', 'dj_voice_provider', 'dj_profanity_filter', "
        "'station_name', 'stream_bitrate', 'stream_format', "
        "'crossfade_duration', 'ui_theme', 'ui_show_artwork', "
        "'ui_history_limit', 'enable_commentary', 'enable_track_enrichment', "
        "'enable_artwork_lookup'"
        ")"
    )