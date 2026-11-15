"""Create persisted moderation assessments."""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "assessments",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("ad_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("policy_version", sa.String(128), nullable=False),
        sa.Column("scores", sa.JSON(), nullable=False),
        sa.Column("model", sa.String(255), nullable=False),
        sa.Column("usage", sa.JSON(), nullable=False),
        sa.Column("categories", sa.JSON(), nullable=False),
        sa.Column("reason", sa.String(1000), nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "ad_id",
            "user_id",
            "content_hash",
            "policy_version",
            name="uq_assessment_content_policy",
        ),
    )
    op.create_index(
        "ix_assessments_user_checked", "assessments", ["user_id", "checked_at"]
    )


def downgrade() -> None:
    op.drop_table("assessments")
