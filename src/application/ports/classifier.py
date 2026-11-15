from abc import ABC, abstractmethod

from src.domain.entities import AdSnapshot, Signals


class ClassifierUnavailable(Exception):
    """No trusted model result is available; the ad has not been approved."""


class Classifier(ABC):
    @abstractmethod
    async def classify(self, snapshot: AdSnapshot) -> Signals: ...
