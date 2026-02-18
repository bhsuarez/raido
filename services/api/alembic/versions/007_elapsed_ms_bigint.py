"""change elapsed_ms to bigint

Revision ID: 007_elapsed_ms_bigint
Revises: 056a5f22cfdb
Create Date: 2026-02-18

"""
from alembic import op
import sqlalchemy as sa

revision = '007_elapsed_ms_bigint'
down_revision = '056a5f22cfdb'
branch_labels = None
depends_on = None

def upgrade():
    op.alter_column('plays', 'elapsed_ms',
                    existing_type=sa.Integer(),
                    type_=sa.BigInteger(),
                    existing_nullable=True)

def downgrade():
    op.alter_column('plays', 'elapsed_ms',
                    existing_type=sa.BigInteger(),
                    type_=sa.Integer(),
                    existing_nullable=True)
