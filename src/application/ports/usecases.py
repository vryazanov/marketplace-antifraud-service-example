from abc import ABC, abstractmethod

from src.domain.entities import AdSnapshot, CheckResult


class CheckAdPort(ABC):
    @abstractmethod
    async def execute(self, snapshot: AdSnapshot) -> CheckResult: ...
