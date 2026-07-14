"""add phone to auth users

Revision ID: 3c9e1c2b8a10
Revises: 7f4d4c6f1a22
Create Date: 2026-07-14 02:05:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "3c9e1c2b8a10"
down_revision: Union[str, Sequence[str], None] = "7f4d4c6f1a22"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("auth_users", sa.Column("phone", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("auth_users", "phone")
