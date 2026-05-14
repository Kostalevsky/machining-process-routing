"""add user profile fields

Revision ID: 20260512_0003
Revises: 20260412_0002
Create Date: 2026-05-12 00:00:00
"""

import sqlalchemy as sa
from alembic import op

revision = "20260512_0003"
down_revision = "20260412_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("full_name", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("company", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("role", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("description", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "description")
    op.drop_column("users", "role")
    op.drop_column("users", "company")
    op.drop_column("users", "full_name")
