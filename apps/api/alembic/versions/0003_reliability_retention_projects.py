"""Add retention, reliable jobs, semantic metadata and project audit domain.

Revision ID: 0003
Revises: 0002
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE jobstatus ADD VALUE IF NOT EXISTS 'DEAD_LETTER'")
    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", sa.String(128), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_projects_owner_id", "projects", ["owner_id"])
    op.add_column(
        "segments",
        sa.Column(
            "semantic_metadata",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column("editing_sessions", sa.Column("project_id", postgresql.UUID(), nullable=True))
    op.add_column("editing_sessions", sa.Column("transient_expires_at", sa.DateTime(timezone=True)))
    op.add_column("editing_sessions", sa.Column("expired_at", sa.DateTime(timezone=True)))
    op.add_column("editing_sessions", sa.Column("deleted_at", sa.DateTime(timezone=True)))
    op.create_foreign_key(
        "fk_editing_sessions_project_id",
        "editing_sessions",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_editing_sessions_project_id", "editing_sessions", ["project_id"])
    op.add_column("jobs", sa.Column("idempotency_key", sa.String(255)))
    op.add_column("jobs", sa.Column("attempts", sa.Integer(), server_default="0", nullable=False))
    op.add_column(
        "jobs", sa.Column("max_attempts", sa.Integer(), server_default="3", nullable=False)
    )
    op.add_column(
        "jobs",
        sa.Column(
            "available_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.add_column("jobs", sa.Column("lease_expires_at", sa.DateTime(timezone=True)))
    op.add_column("jobs", sa.Column("heartbeat_at", sa.DateTime(timezone=True)))
    op.add_column("jobs", sa.Column("cancel_requested_at", sa.DateTime(timezone=True)))
    op.add_column("jobs", sa.Column("expires_at", sa.DateTime(timezone=True)))
    op.add_column("jobs", sa.Column("redacted_at", sa.DateTime(timezone=True)))
    op.add_column(
        "jobs",
        sa.Column(
            "checkpoint", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False
        ),
    )
    op.create_index("ix_jobs_expires_at", "jobs", ["expires_at"])
    op.create_unique_constraint(
        "uq_jobs_owner_kind_idempotency", "jobs", ["owner_id", "kind", "idempotency_key"]
    )
    op.create_table(
        "audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("owner_id", sa.String(128), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("editing_session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(128), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["editing_session_id"], ["editing_sessions.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_events_owner_id", "audit_events", ["owner_id"])
    op.create_index("ix_audit_events_project_id", "audit_events", ["project_id"])
    op.create_index("ix_audit_events_editing_session_id", "audit_events", ["editing_session_id"])
    op.create_index("ix_audit_events_event_type", "audit_events", ["event_type"])


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_constraint("uq_jobs_owner_kind_idempotency", "jobs", type_="unique")
    op.drop_index("ix_jobs_expires_at", table_name="jobs")
    for column in (
        "checkpoint",
        "redacted_at",
        "expires_at",
        "cancel_requested_at",
        "heartbeat_at",
        "lease_expires_at",
        "available_at",
        "max_attempts",
        "attempts",
        "idempotency_key",
    ):
        op.drop_column("jobs", column)
    op.drop_index("ix_editing_sessions_project_id", table_name="editing_sessions")
    op.drop_constraint("fk_editing_sessions_project_id", "editing_sessions", type_="foreignkey")
    for column in ("deleted_at", "expired_at", "transient_expires_at", "project_id"):
        op.drop_column("editing_sessions", column)
    op.drop_column("segments", "semantic_metadata")
    op.drop_table("projects")
    op.execute("UPDATE jobs SET status = 'FAILED' WHERE status = 'DEAD_LETTER'")
    op.execute("ALTER TABLE graph_runs ALTER COLUMN status TYPE VARCHAR USING status::text")
    op.execute("ALTER TABLE jobs ALTER COLUMN status TYPE VARCHAR USING status::text")
    op.execute("DROP TYPE jobstatus")
    op.execute(
        "CREATE TYPE jobstatus AS ENUM ('QUEUED','RUNNING','SUCCEEDED','FAILED','CANCELLED')"
    )
    op.execute("ALTER TABLE jobs ALTER COLUMN status TYPE jobstatus USING status::jobstatus")
    op.execute("ALTER TABLE graph_runs ALTER COLUMN status TYPE jobstatus USING status::jobstatus")
