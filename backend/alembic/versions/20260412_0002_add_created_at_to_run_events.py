"""add created_at to run_events

Revision ID: 20260412_0002
Revises: 20260321_0001
Create Date: 2026-04-12 17:30:00
"""

import sqlalchemy as sa
from alembic import op

revision = "20260412_0002"
down_revision = "20260321_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "run_events",
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_column("run_events", "created_at")
