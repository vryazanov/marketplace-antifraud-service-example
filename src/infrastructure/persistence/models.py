from datetime import datetime

from sqlalchemy import JSON, BigInteger, DateTime, Index, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class AssessmentModel(Base):
    __tablename__ = "assessments"
    __table_args__ = (
        UniqueConstraint(
            "ad_id",
            "user_id",
            "content_hash",
            "policy_version",
            name="uq_assessment_content_policy",
        ),
        Index("ix_assessments_user_checked", "user_id", "checked_at"),
    )
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    ad_id: Mapped[int] = mapped_column(BigInteger)
    user_id: Mapped[int] = mapped_column(BigInteger)
    content_hash: Mapped[str] = mapped_column(String(64))
    policy_version: Mapped[str] = mapped_column(String(128))
    scores: Mapped[dict] = mapped_column(JSON)
    model: Mapped[str] = mapped_column(String(255))
    usage: Mapped[dict] = mapped_column(JSON)
    categories: Mapped[list] = mapped_column(JSON)
    reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
