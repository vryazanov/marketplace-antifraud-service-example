import hashlib
from datetime import datetime

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.ports.repositories import AssessmentRepository
from src.domain.entities import Assessment, Category, Decision, Signals
from src.infrastructure.persistence.models import AssessmentModel


class SQLAlchemyAssessmentRepository(AssessmentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def lock_user(self, user_id: int) -> None:
        key = int.from_bytes(
            hashlib.sha256(f"antifraud:{user_id}".encode()).digest()[:8], signed=True
        )
        await self._session.execute(
            text("SELECT pg_advisory_xact_lock(:key)"), {"key": key}
        )

    async def find(
        self, ad_id: int, user_id: int, content_hash: str, policy_version: str
    ) -> Assessment | None:
        row = await self._session.scalar(
            select(AssessmentModel).where(
                AssessmentModel.ad_id == ad_id,
                AssessmentModel.user_id == user_id,
                AssessmentModel.content_hash == content_hash,
                AssessmentModel.policy_version == policy_version,
            )
        )
        if row is None:
            return None
        categories = tuple(Category(c) for c in row.categories)
        return Assessment(
            row.ad_id,
            row.user_id,
            row.content_hash,
            row.policy_version,
            Signals(
                {Category(k): v for k, v in row.scores.items()}, row.model, row.usage
            ),
            Decision(bool(categories), row.reason, categories),
            row.checked_at,
        )

    async def add(self, a: Assessment) -> None:
        self._session.add(
            AssessmentModel(
                ad_id=a.ad_id,
                user_id=a.user_id,
                content_hash=a.content_hash,
                policy_version=a.policy_version,
                scores=a.signals.scores,
                model=a.signals.model,
                usage=a.signals.usage,
                categories=list(a.decision.categories),
                reason=a.decision.reason,
                checked_at=a.checked_at,
            )
        )
        await self._session.flush()

    async def count_fraud_ads(self, user_id: int, since: datetime) -> int:
        # JSON containment for categories is avoided: scores + persisted policy
        # decision carry the fraud category, queried as a JSON array in PostgreSQL.
        stmt = select(func.count(func.distinct(AssessmentModel.ad_id))).where(
            AssessmentModel.user_id == user_id,
            AssessmentModel.checked_at >= since,
            text("categories::jsonb @> '[\"fraud\"]'::jsonb"),
        )
        return (await self._session.scalar(stmt)) or 0
