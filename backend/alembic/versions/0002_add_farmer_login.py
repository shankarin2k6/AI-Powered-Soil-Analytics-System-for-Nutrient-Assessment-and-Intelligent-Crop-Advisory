"""add farmer login

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-16 03:27:00.507203
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0002'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('farmers', sa.Column('password_hash', sa.String(length=200), nullable=True))
    op.create_index(op.f('ix_farmers_phone'), 'farmers', ['phone'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_farmers_phone'), table_name='farmers')
    op.drop_column('farmers', 'password_hash')
