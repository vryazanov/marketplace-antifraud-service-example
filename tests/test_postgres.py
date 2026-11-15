import asyncio
import os
import secrets
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.application.usecases.check_ad import CheckAd
from src.domain.entities import Category, Policy
from src.infrastructure.persistence.models import AssessmentModel
from src.infrastructure.persistence.uow import SQLAlchemyUnitOfWork
from tests.conftest import FakeClassifier

pytestmark = pytest.mark.skipif(
    not os.environ.get("TEST_DATABASE_URL"), reason="Separate PostgreSQL required"
)


async def test_concurrent_idempotency_and_rolling_distinct_count(snapshot):
    engine = create_async_engine(os.environ["TEST_DATABASE_URL"])
    factory = async_sessionmaker(engine, expire_on_commit=False)
    user_id = secrets.randbelow(10**12) + 10**12
    snapshot = replace(snapshot, user_id=user_id)

    class SlowClassifier(FakeClassifier):
        async def classify(self, snapshot):
            await asyncio.sleep(0.05)
            return await super().classify(snapshot)

    classifier = SlowClassifier((Category.FRAUD,))
    now = datetime.now(UTC)

    def check(clock=lambda: now):
        return CheckAd(SQLAlchemyUnitOfWork(factory), classifier, Policy(), clock)

    try:
        a, b = await asyncio.gather(
            check().execute(snapshot), check().execute(snapshot)
        )
        assert a.assessment == b.assessment and classifier.calls == 1
        assert a.fraud_ads_in_week == b.fraud_ads_in_week == 1
        await check().execute(replace(snapshot, description="Другой текст"))
        await check(lambda: now - timedelta(days=8)).execute(
            replace(snapshot, ad_id=80)
        )
        result = await check().execute(replace(snapshot, ad_id=2))
        assert result.fraud_ads_in_week == 2 and not result.soft_delete_required
        result = await check().execute(replace(snapshot, ad_id=3))
        assert result.fraud_ads_in_week == 3 and result.soft_delete_required
        async with factory() as session:
            assert (
                await session.scalar(
                    select(func.count())
                    .select_from(AssessmentModel)
                    .where(AssessmentModel.user_id == user_id)
                )
                == 5
            )
    finally:
        async with factory() as session:
            await session.execute(
                delete(AssessmentModel).where(AssessmentModel.user_id == user_id)
            )
            await session.commit()
        await engine.dispose()
