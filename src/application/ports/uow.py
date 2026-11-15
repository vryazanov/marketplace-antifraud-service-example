from abc import ABC, abstractmethod
from types import TracebackType

from src.application.ports.repositories import AssessmentRepository


class UnitOfWork(ABC):
    assessments: AssessmentRepository

    @abstractmethod
    async def __aenter__(self) -> "UnitOfWork": ...

    @abstractmethod
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None: ...

    @abstractmethod
    async def commit(self) -> None: ...
