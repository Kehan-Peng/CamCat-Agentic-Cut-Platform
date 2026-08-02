"""Initial CamCat schema (immutable historical definition).

Revision ID: 0001
Revises: None
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

asset_status = postgresql.ENUM(
    "UPLOADED", "PROCESSING", "READY", "FAILED", name="assetstatus", create_type=False
)
job_status = postgresql.ENUM(
    "QUEUED", "RUNNING", "SUCCEEDED", "FAILED", "CANCELLED", name="jobstatus", create_type=False
)
job_kind = postgresql.ENUM("INGEST_MEDIA", "RENDER", name="jobkind", create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    asset_status.create(bind, checkfirst=True)
    job_status.create(bind, checkfirst=True)
    job_kind.create(bind, checkfirst=True)
    op.create_table(
        "assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", sa.String(128), nullable=False),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("content_type", sa.String(128), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("storage_key", sa.String(1024), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("status", asset_status, nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("license_name", sa.String(255), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key"),
    )
    op.create_index("ix_assets_owner_id", "assets", ["owner_id"])
    op.create_table(
        "editing_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", sa.String(128), nullable=False),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("current_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_editing_sessions_owner_id", "editing_sessions", ["owner_id"])
    op.create_table(
        "segments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("start_time", sa.Float(), nullable=False),
        sa.Column("end_time", sa.Float(), nullable=False),
        sa.Column("trigger_type", sa.String(64), nullable=False),
        sa.Column("storage_key", sa.String(1024), nullable=False),
        sa.Column("thumbnail_key", sa.String(1024), nullable=True),
        sa.Column("description_text", sa.Text(), nullable=False),
        sa.Column("tags", postgresql.JSONB(), nullable=False),
        sa.Column("event_type", sa.String(128), nullable=True),
        sa.Column("risk_score", sa.Float(), nullable=False),
        sa.Column("embedding_model", sa.String(255), nullable=False),
        sa.Column("embedding_dimension", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset_id", "start_time", "end_time"),
    )
    op.create_index("ix_segments_asset_id", "segments", ["asset_id"])
    op.create_table(
        "state_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("document", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["editing_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", "version"),
    )
    op.create_index("ix_state_versions_session_id", "state_versions", ["session_id"])
    op.create_table(
        "state_patches",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("base_version", sa.Integer(), nullable=False),
        sa.Column("result_version", sa.Integer(), nullable=False),
        sa.Column("operations", postgresql.JSONB(), nullable=False),
        sa.Column("actor", sa.String(128), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["editing_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_state_patches_session_id", "state_patches", ["session_id"])
    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", sa.String(128), nullable=False),
        sa.Column("kind", job_kind, nullable=False),
        sa.Column("status", job_status, nullable=False),
        sa.Column("progress", sa.Float(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("result", postgresql.JSONB(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("worker_id", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_jobs_owner_id", "jobs", ["owner_id"])
    op.create_index("ix_jobs_status", "jobs", ["status"])
    op.create_table(
        "graph_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", sa.String(128), nullable=False),
        sa.Column("thread_id", sa.String(255), nullable=False),
        sa.Column("editing_session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("state", postgresql.JSONB(), nullable=False),
        sa.Column("node_trace", postgresql.JSONB(), nullable=False),
        sa.Column("status", job_status, nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["editing_session_id"], ["editing_sessions.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_graph_runs_owner_id", "graph_runs", ["owner_id"])
    op.create_index("ix_graph_runs_thread_id", "graph_runs", ["thread_id"])


def downgrade() -> None:
    for table in (
        "graph_runs",
        "jobs",
        "state_patches",
        "state_versions",
        "segments",
        "editing_sessions",
        "assets",
    ):
        op.drop_table(table)
    bind = op.get_bind()
    job_kind.drop(bind, checkfirst=True)
    job_status.drop(bind, checkfirst=True)
    asset_status.drop(bind, checkfirst=True)
