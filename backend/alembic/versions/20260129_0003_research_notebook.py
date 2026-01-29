"""research notebook tables

Revision ID: 20260129_0003
Revises: 20260125_0002
Create Date: 2026-01-29 11:00:00
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260129_0003"
down_revision = "20260125_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "research_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            server_onupdate=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_research_sessions_session_id", "research_sessions", ["session_id"])

    op.create_table(
        "research_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("research_id", sa.Integer(), sa.ForeignKey("research_sessions.id"), nullable=False),
        sa.Column("entry_type", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tool_traces_json", sa.JSON(), nullable=True),
        sa.Column("sources_json", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_research_entries_research_id", "research_entries", ["research_id"])


def downgrade() -> None:
    op.drop_table("research_entries")
    op.drop_table("research_sessions")
