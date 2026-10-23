"""add optional farmer profile details (email, address)

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-20 07:30:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0003'
down_revision: Union[str, None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('farmers', sa.Column('email', sa.String(length=254), nullable=True))
    op.add_column('farmers', sa.Column('address', sa.String(length=300), nullable=True))


def downgrade() -> None:
    op.drop_column('farmers', 'address')
    op.drop_column('farmers', 'email')
