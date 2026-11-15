from abc import ABC, abstractmethod
from datetime import datetime

from src.domain.entities import Assessment


class AssessmentRepository(ABC):
    @abstractmethod
    async def lock_user(self, user_id: int) -> None: ...

    @abstractmethod
    async def find(
        self, ad_id: int, user_id: int, content_hash: str, policy_version: str
    ) -> Assessment | None: ...

    @abstractmethod
    async def add(self, assessment: Assessment) -> None: ...

    @abstractmethod
    async def count_fraud_ads(self, user_id: int, since: datetime) -> int: ...
