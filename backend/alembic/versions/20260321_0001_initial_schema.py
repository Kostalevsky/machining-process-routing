"""initial schema

Revision ID: 20260321_0001
Revises:
Create Date: 2026-03-21 15:45:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260321_0001"
down_revision = None
branch_labels = None
depends_on = None


run_status = sa.Enum(
    "created",
    "source_uploaded",
    "rendering",
    "rendered",
    "collages_ready",
    "generating_json",
    "completed",
    "failed",
    name="run_status",
)

artifact_type = sa.Enum(
    "source_obj",
    "render",
    "collage",
    "generated_json",
    name="artifact_type",
)

generation_status = sa.Enum(
    "pending",
    "running",
    "succeeded",
    "failed",
    name="generation_status",
)


def upgrade() -> None:
    bind = op.get_bind()
    run_status.create(bind, checkfirst=True)
    artifact_type.create(bind, checkfirst=True)
    generation_status.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("status", run_status, nullable=False, server_default="created"),
        sa.Column("source_artifact_id", sa.Integer(), nullable=True),
        sa.Column("selected_collage_artifact_id", sa.Integer(), nullable=True),
        sa.Column("latest_generation_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_runs_user_id", "runs", ["user_id"], unique=False)

    op.create_table(
        "artifacts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.Integer(), sa.ForeignKey("runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", artifact_type, nullable=False),
        sa.Column("bucket", sa.String(length=255), nullable=False),
        sa.Column("object_key", sa.String(length=1024), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("checksum", sa.String(length=128), nullable=True),
        sa.Column("meta_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_artifacts_run_id", "artifacts", ["run_id"], unique=False)
    op.create_index("ix_artifacts_user_id", "artifacts", ["user_id"], unique=False)

    op.create_table(
        "generations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.Integer(), sa.ForeignKey("runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("input_collage_artifact_id", sa.Integer(), sa.ForeignKey("artifacts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("output_artifact_id", sa.Integer(), sa.ForeignKey("artifacts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("provider", sa.String(length=100), nullable=True),
        sa.Column("model_name", sa.String(length=255), nullable=True),
        sa.Column("prompt_version", sa.String(length=100), nullable=True),
        sa.Column("status", generation_status, nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_generations_run_id", "generations", ["run_id"], unique=False)
    op.create_index("ix_generations_user_id", "generations", ["user_id"], unique=False)

    op.create_table(
        "run_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.Integer(), sa.ForeignKey("runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=True),
    )
    op.create_index("ix_run_events_run_id", "run_events", ["run_id"], unique=False)

    op.create_foreign_key(
        "fk_runs_source_artifact_id_artifacts",
        "runs",
        "artifacts",
        ["source_artifact_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_runs_selected_collage_artifact_id_artifacts",
        "runs",
        "artifacts",
        ["selected_collage_artifact_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_runs_latest_generation_id_generations",
        "runs",
        "generations",
        ["latest_generation_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_runs_latest_generation_id_generations", "runs", type_="foreignkey")
    op.drop_constraint("fk_runs_selected_collage_artifact_id_artifacts", "runs", type_="foreignkey")
    op.drop_constraint("fk_runs_source_artifact_id_artifacts", "runs", type_="foreignkey")

    op.drop_index("ix_run_events_run_id", table_name="run_events")
    op.drop_table("run_events")

    op.drop_index("ix_generations_user_id", table_name="generations")
    op.drop_index("ix_generations_run_id", table_name="generations")
    op.drop_table("generations")

    op.drop_index("ix_artifacts_user_id", table_name="artifacts")
    op.drop_index("ix_artifacts_run_id", table_name="artifacts")
    op.drop_table("artifacts")

    op.drop_index("ix_runs_user_id", table_name="runs")
    op.drop_table("runs")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

    bind = op.get_bind()
    generation_status.drop(bind, checkfirst=True)
    artifact_type.drop(bind, checkfirst=True)
    run_status.drop(bind, checkfirst=True)
