"""quiz and profile tables

Revision ID: 20260125_0002
Revises: 20260123_0001
Create Date: 2026-01-25 12:10:00
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260125_0002"
down_revision = "20260123_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "quizzes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("difficulty_plan_json", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_quizzes_document_id", "quizzes", ["document_id"])
    op.create_index("ix_quizzes_session_id", "quizzes", ["session_id"])

    op.create_table(
        "quiz_questions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("quiz_id", sa.Integer(), sa.ForeignKey("quizzes.id"), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("difficulty", sa.String(length=16), nullable=False),
        sa.Column("stem", sa.Text(), nullable=False),
        sa.Column("options_json", sa.JSON(), nullable=True),
        sa.Column("answer_json", sa.JSON(), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("related_concept", sa.String(length=255), nullable=True),
        sa.Column("source_chunk_ids_json", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_quiz_questions_quiz_id", "quiz_questions", ["quiz_id"])

    op.create_table(
        "quiz_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("quiz_id", sa.Integer(), sa.ForeignKey("quizzes.id"), nullable=False),
        sa.Column(
            "submitted_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("accuracy", sa.Float(), nullable=True),
        sa.Column("summary_json", sa.JSON(), nullable=True),
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_quiz_attempts_quiz_id", "quiz_attempts", ["quiz_id"])

    op.create_table(
        "concept_stats",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("concept", sa.String(length=255), nullable=False),
        sa.Column("correct_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("wrong_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_seen", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("session_id", "concept", name="uq_concept_stats_session_concept"),
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_concept_stats_session_id", "concept_stats", ["session_id"])

    op.create_table(
        "learner_profile",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("ability_level", sa.String(length=32), nullable=True),
        sa.Column("theta", sa.Float(), nullable=True),
        sa.Column("frustration_score", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "last_updated",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.UniqueConstraint("session_id", name="uq_learner_profile_session_id"),
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_learner_profile_session_id", "learner_profile", ["session_id"])


def downgrade() -> None:
    op.drop_table("learner_profile")

    op.drop_table("concept_stats")

    op.drop_table("quiz_attempts")

    op.drop_table("quiz_questions")

    op.drop_table("quizzes")
