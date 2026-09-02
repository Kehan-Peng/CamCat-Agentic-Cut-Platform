"""Add the transient source analysis job kind.

Revision ID: 0002
Revises: 0001
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE jobkind ADD VALUE IF NOT EXISTS 'ANALYZE_SOURCE'")


def downgrade() -> None:
    op.execute("DELETE FROM jobs WHERE kind = 'ANALYZE_SOURCE'")
    op.execute("ALTER TABLE jobs ALTER COLUMN kind TYPE VARCHAR USING kind::text")
    op.execute("DROP TYPE jobkind")
    op.execute("CREATE TYPE jobkind AS ENUM ('INGEST_MEDIA', 'RENDER')")
    op.execute("ALTER TABLE jobs ALTER COLUMN kind TYPE jobkind USING kind::jobkind")
