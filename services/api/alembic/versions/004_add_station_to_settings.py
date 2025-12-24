"""add station to settings

Revision ID: 004_add_station
Revises: 003_add_stations
Create Date: 2025-10-16 12:20:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade():
    # Add station column with default value
    op.add_column('settings', sa.Column('station', sa.String(length=50), nullable=False, server_default='main'))

    # Create index on station column
    op.create_index(op.f('ix_settings_station'), 'settings', ['station'], unique=False)

    # Drop old unique index on key
    op.drop_index('ix_settings_key', 'settings')

    # Add new unique constraint on (key, station)
    op.create_unique_constraint('uix_key_station', 'settings', ['key', 'station'])


def downgrade():
    # Remove unique constraint on (key, station)
    op.drop_constraint('uix_key_station', 'settings', type_='unique')

    # Restore unique index on key
    op.create_index('ix_settings_key', 'settings', ['key'], unique=True)

    # Drop index on station
    op.drop_index(op.f('ix_settings_station'), table_name='settings')

    # Drop station column
    op.drop_column('settings', 'station')
