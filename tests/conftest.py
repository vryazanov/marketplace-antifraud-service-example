from datetime import UTC, datetime

import pytest

from src.application.ports.classifier import Classifier
from src.domain.entities import AdSnapshot, Category, Signals


@pytest.fixture
def snapshot():
    return AdSnapshot(
        1, 1, "Телефон", "Можно проверить при встрече", 1000, "electronics", "Москва"
    )


@pytest.fixture
def now():
    return datetime(2026, 11, 15, 12, tzinfo=UTC)


class FakeClassifier(Classifier):
    def __init__(self, categories=()):
        self.calls = 0
        self.categories = categories

    async def classify(self, snapshot):
        self.calls += 1
        return Signals(
            {c: 0.95 if c in self.categories else 0.05 for c in Category},
            "test-jev",
            {"requests_charged": 5, "remaining_requests": 100},
        )
