"""add the stored_files table (photos kept in the database, for hosts with a temporary disk)

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-18 18:00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0004'
down_revision: Union[str, None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('stored_files',
                    sa.Column('key', sa.String(length=300), primary_key=True),
                    sa.Column('data', sa.LargeBinary(), nullable=False))


def downgrade() -> None:
    op.drop_table('stored_files')
