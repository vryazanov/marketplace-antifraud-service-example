import hashlib
import json
import math
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class Category(StrEnum):
    FRAUD = "fraud"
    SPAM = "spam"
    ADVERTISING = "advertising"
    THREATS = "threats"
    VIOLENCE = "violence"


REASONS = {
    Category.FRAUD: "Обнаружены признаки мошенничества.",
    Category.SPAM: "Объявление содержит спам.",
    Category.ADVERTISING: "Объявление содержит нежелательную рекламу.",
    Category.THREATS: "Объявление содержит угрозы.",
    Category.VIOLENCE: "Объявление содержит признаки насилия.",
}


@dataclass(frozen=True)
class AdSnapshot:
    ad_id: int
    user_id: int
    title: str
    description: str
    price: int
    category: str
    city: str

    def state(self) -> str:
        # Identifiers never go to the model: only the content to classify.
        return json.dumps(
            {
                "title": self.title,
                "description": self.description,
                "price": self.price,
                "category": self.category,
                "city": self.city,
            },
            ensure_ascii=False,
            sort_keys=True,
        )

    def fingerprint(self) -> str:
        return hashlib.sha256(self.state().encode()).hexdigest()


@dataclass(frozen=True)
class Signals:
    scores: dict[Category, float]
    model: str
    usage: dict[str, int]

    def __post_init__(self) -> None:
        if set(self.scores) != set(Category):
            raise ValueError("All five moderation signals are required")
        if not all(
            type(v) in (int, float) and math.isfinite(v) and 0 <= v <= 1
            for v in self.scores.values()
        ):
            raise ValueError("Signals must be finite probabilities")
        if not self.model:
            raise ValueError("Model identifier is required")


@dataclass(frozen=True)
class Decision:
    blocked: bool
    reason: str | None
    categories: tuple[Category, ...]


@dataclass(frozen=True)
class Policy:
    threshold: float = 0.85
    prompt_version: str = "jev-questions-v1"

    def __post_init__(self) -> None:
        if not math.isfinite(self.threshold) or not 0 < self.threshold <= 1:
            raise ValueError("Threshold must be in (0, 1]")

    @property
    def version(self) -> str:
        return f"{self.prompt_version}:threshold={self.threshold:g}"

    def decide(self, signals: Signals) -> Decision:
        categories = tuple(c for c in Category if signals.scores[c] >= self.threshold)
        return Decision(
            bool(categories),
            " ".join(REASONS[c] for c in categories) if categories else None,
            categories,
        )


@dataclass(frozen=True)
class Assessment:
    ad_id: int
    user_id: int
    content_hash: str
    policy_version: str
    signals: Signals
    decision: Decision
    checked_at: datetime


@dataclass(frozen=True)
class CheckResult:
    assessment: Assessment
    fraud_ads_in_week: int
    soft_delete_required: bool
