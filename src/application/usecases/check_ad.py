from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from src.application.ports.classifier import Classifier
from src.application.ports.uow import UnitOfWork
from src.application.ports.usecases import CheckAdPort
from src.domain.entities import AdSnapshot, Assessment, CheckResult, Policy


class CheckAd(CheckAdPort):
    def __init__(
        self,
        uow: UnitOfWork,
        classifier: Classifier,
        policy: Policy,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._uow = uow
        self._classifier = classifier
        self._policy = policy
        self._clock = clock or (lambda: datetime.now(UTC))

    async def execute(self, snapshot: AdSnapshot) -> CheckResult:
        async with self._uow:
            # Serialize checks of one seller to deduplicate paid requests and counts.
            # The HTTP timeout bounds how long this transaction holds its lock.
            await self._uow.assessments.lock_user(snapshot.user_id)
            assessment = await self._uow.assessments.find(
                snapshot.ad_id,
                snapshot.user_id,
                snapshot.fingerprint(),
                self._policy.version,
            )
            if assessment is None:
                signals = await self._classifier.classify(snapshot)
                assessment = Assessment(
                    snapshot.ad_id,
                    snapshot.user_id,
                    snapshot.fingerprint(),
                    self._policy.version,
                    signals,
                    self._policy.decide(signals),
                    self._clock(),
                )
                await self._uow.assessments.add(assessment)
            count = await self._uow.assessments.count_fraud_ads(
                snapshot.user_id, self._clock() - timedelta(days=7)
            )
            await self._uow.commit()
        return CheckResult(assessment, count, count >= 3)
