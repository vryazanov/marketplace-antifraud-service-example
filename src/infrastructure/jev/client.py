import httpx

from src.application.ports.classifier import Classifier, ClassifierUnavailable
from src.domain.entities import AdSnapshot, Category, Signals
from src.infrastructure.jev.questions import QUESTIONS


class JevClassifier(Classifier):
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def classify(self, snapshot: AdSnapshot) -> Signals:
        try:
            response = await self._client.post(
                "answers", json={"state": snapshot.state(), "questions": QUESTIONS}
            )
            response.raise_for_status()
            data = response.json()
            answers = data["answers"]
            scores = {}
            for category in Category:
                answer = answers[category.value]
                if answer["type"] != "noul":
                    raise ValueError("Unexpected answer type")
                scores[category] = answer["noul"]
            model = data["model"]
            if not isinstance(model, str):
                raise ValueError("Invalid model name")
            usage = data["usage"]
            for field in ("requests_charged", "remaining_requests"):
                if type(usage[field]) is not int or usage[field] < 0:
                    raise ValueError("Invalid usage")
            return Signals(
                scores,
                model,
                {k: usage[k] for k in ("requests_charged", "remaining_requests")},
            )
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            # Never include upstream bodies, headers or credentials in API errors.
            raise ClassifierUnavailable(
                "Jev is unavailable or returned invalid data"
            ) from exc


class UnconfiguredClassifier(Classifier):
    async def classify(self, snapshot: AdSnapshot) -> Signals:
        raise ClassifierUnavailable("Jev credentials are not configured")
