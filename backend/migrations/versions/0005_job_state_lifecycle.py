"""expand job state lifecycle metadata

Revision ID: 0005_job_state_lifecycle
Revises: 0004_invites_and_org_thresholds
Create Date: 2026-03-05
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0005_job_state_lifecycle"
down_revision = "0004_invites_and_org_thresholds"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("job_states", sa.Column("created_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("job_states", sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("job_states", sa.Column("task_id", sa.String(length=100), nullable=True))
    op.add_column("job_states", sa.Column("task_name", sa.String(length=100), nullable=True))
    op.add_column("job_states", sa.Column("progress", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("job_states", sa.Column("request_id", sa.String(length=100), nullable=True))
    op.add_column("job_states", sa.Column("correlation_id", sa.String(length=100), nullable=True))
    op.add_column("job_states", sa.Column("last_error", sa.Text(), nullable=True))
    op.add_column("job_states", sa.Column("traceback_summary", sa.Text(), nullable=True))
    op.add_column("job_states", sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("job_states", sa.Column("last_retry_at", sa.DateTime(timezone=True), nullable=True))

    op.execute("UPDATE job_states SET created_at = updated_at WHERE created_at IS NULL")
    op.execute("UPDATE job_states SET task_name = job_name WHERE task_name IS NULL")
    op.execute("UPDATE job_states SET task_id = id::text WHERE task_id IS NULL")
    op.execute("UPDATE job_states SET status = 'SUCCEEDED' WHERE status = 'DONE'")

    op.alter_column("job_states", "created_at", nullable=False)
    op.alter_column("job_states", "task_name", nullable=False)
    op.alter_column("job_states", "task_id", nullable=False)

    op.create_unique_constraint("uq_job_state_task_id", "job_states", ["task_id"])
    op.create_index("ix_job_states_org_status_created", "job_states", ["org_id", "status", "created_at"])
    op.create_index("ix_job_states_org_task_created", "job_states", ["org_id", "task_name", "created_at"])

    op.alter_column("job_states", "progress", server_default=None)
    op.alter_column("job_states", "retry_count", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_job_states_org_task_created", table_name="job_states")
    op.drop_index("ix_job_states_org_status_created", table_name="job_states")
    op.drop_constraint("uq_job_state_task_id", "job_states", type_="unique")

    op.drop_column("job_states", "last_retry_at")
    op.drop_column("job_states", "retry_count")
    op.drop_column("job_states", "traceback_summary")
    op.drop_column("job_states", "last_error")
    op.drop_column("job_states", "correlation_id")
    op.drop_column("job_states", "request_id")
    op.drop_column("job_states", "progress")
    op.drop_column("job_states", "task_name")
    op.drop_column("job_states", "task_id")
    op.drop_column("job_states", "org_id")
    op.drop_column("job_states", "created_at")
