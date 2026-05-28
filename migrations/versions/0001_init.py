"""init schema

Revision ID: 0001
Revises:
Create Date: 2026-05-12

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pdf_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("s3_key", sa.String(length=512), nullable=False, unique=True),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    job_status = sa.Enum(
        "pending", "processing", "completed", "failed", name="job_status"
    )
    job_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "merge_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "status",
            job_status,
            nullable=False,
            server_default="pending",
        ),
        sa.Column("source_file_ids", sa.JSON(), nullable=False),
        sa.Column("output_s3_key", sa.String(length=512), nullable=True),
        sa.Column("error_message", sa.String(length=1024), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_merge_jobs_status", "merge_jobs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_merge_jobs_status", table_name="merge_jobs")
    op.drop_table("merge_jobs")
    op.drop_table("pdf_files")
    sa.Enum(name="job_status").drop(op.get_bind(), checkfirst=True)
