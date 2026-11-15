from dataclasses import replace
from datetime import timedelta

import pytest

from src.application.ports.classifier import ClassifierUnavailable
from src.application.usecases.check_ad import CheckAd
from src.domain.entities import Category, Policy
from tests.conftest import FakeClassifier


class MemoryUow:
    def __init__(self):
        self.rows = []
        self.assessments = self
        self.commits = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def lock_user(self, user_id):
        pass

    async def find(self, ad_id, user_id, content_hash, policy_version):
        return next(
            (
                a
                for a in self.rows
                if (a.ad_id, a.user_id, a.content_hash, a.policy_version)
                == (ad_id, user_id, content_hash, policy_version)
            ),
            None,
        )

    async def add(self, assessment):
        self.rows.append(assessment)

    async def count_fraud_ads(self, user_id, since):
        return len(
            {
                a.ad_id
                for a in self.rows
                if a.user_id == user_id
                and a.checked_at >= since
                and Category.FRAUD in a.decision.categories
            }
        )

    async def commit(self):
        self.commits += 1


async def test_repeat_and_new_revision_do_not_count_same_ad_twice(snapshot, now):
    uow = MemoryUow()
    classifier = FakeClassifier((Category.FRAUD,))
    usecase = CheckAd(uow, classifier, Policy(), lambda: now)
    first = await usecase.execute(snapshot)
    second = await usecase.execute(snapshot)
    assert first == second and classifier.calls == 1
    revision = await usecase.execute(replace(snapshot, price=2000))
    assert revision.fraud_ads_in_week == 1 and classifier.calls == 2
    await usecase.execute(replace(snapshot, ad_id=2))
    third = await usecase.execute(replace(snapshot, ad_id=3))
    assert third.soft_delete_required and third.fraud_ads_in_week == 3


async def test_only_distinct_sellers_recent_fraud_counts(snapshot, now):
    uow = MemoryUow()
    classifier = FakeClassifier((Category.FRAUD,))
    usecase = CheckAd(uow, classifier, Policy(), lambda: now)
    await CheckAd(uow, classifier, Policy(), lambda: now - timedelta(days=8)).execute(
        replace(snapshot, ad_id=99)
    )
    await usecase.execute(replace(snapshot, user_id=9, ad_id=100))
    await CheckAd(uow, FakeClassifier((Category.SPAM,)), Policy(), lambda: now).execute(
        replace(snapshot, ad_id=101)
    )
    result = await usecase.execute(snapshot)
    assert result.fraud_ads_in_week == 1 and not result.soft_delete_required
    # Replaying an old cached decision must not refresh the violation timestamp.
    old = await usecase.execute(replace(snapshot, ad_id=99))
    assert old.fraud_ads_in_week == 1


async def test_new_policy_rechecks_same_content(snapshot, now):
    uow = MemoryUow()
    classifier = FakeClassifier()
    await CheckAd(uow, classifier, Policy(), lambda: now).execute(snapshot)
    await CheckAd(uow, classifier, Policy(0.8), lambda: now).execute(snapshot)
    assert classifier.calls == 2


async def test_unavailable_model_never_saves_an_approval(snapshot, now):
    class Unavailable(FakeClassifier):
        async def classify(self, snapshot):
            raise ClassifierUnavailable("no budget")

    uow = MemoryUow()
    with pytest.raises(ClassifierUnavailable):
        await CheckAd(uow, Unavailable(), Policy(), lambda: now).execute(snapshot)
    assert not uow.rows and not uow.commits
