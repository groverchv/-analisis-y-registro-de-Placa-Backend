"""add auth users table

Revision ID: 2d3f62138b11
Revises: d897435e4fd9
Create Date: 2026-07-13 21:05:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2d3f62138b11"
down_revision: Union[str, Sequence[str], None] = "d897435e4fd9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "auth_users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("full_name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_auth_users_email"), "auth_users", ["email"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_auth_users_email"), table_name="auth_users")
    op.drop_table("auth_users")
