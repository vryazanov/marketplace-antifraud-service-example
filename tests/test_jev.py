import json

import httpx
import pytest

from src.application.ports.classifier import ClassifierUnavailable
from src.domain.entities import Category
from src.infrastructure.jev.client import JevClassifier


def payload():
    return {
        "model": "jev-test",
        "answers": {c.value: {"type": "noul", "noul": 0.1} for c in Category},
        "usage": {"requests_charged": 5, "remaining_requests": 20},
    }


async def test_gateway_contract_and_content_only(snapshot):
    def handler(request):
        assert str(request.url) == "https://gateway.test/v1/answers"
        assert request.headers["x-api-key"] == "test-key"
        data = json.loads(request.content)
        assert set(data) == {"state", "questions"} and len(data["questions"]) == 5
        assert "user_id" not in data["state"] and "ad_id" not in data["state"]
        return httpx.Response(200, json=payload())

    async with httpx.AsyncClient(
        base_url="https://gateway.test/v1/",
        headers={"x-api-key": "test-key"},
        transport=httpx.MockTransport(handler),
    ) as client:
        signals = await JevClassifier(client).classify(snapshot)
    assert signals.model == "jev-test" and signals.usage["requests_charged"] == 5


@pytest.mark.parametrize("status", [401, 429, 500])
async def test_http_errors_are_not_decisions(status, snapshot):
    async with httpx.AsyncClient(
        base_url="https://gateway.test/v1/",
        transport=httpx.MockTransport(lambda r: httpx.Response(status, text="secret")),
    ) as c:
        with pytest.raises(ClassifierUnavailable, match="invalid data") as error:
            await JevClassifier(c).classify(snapshot)
    assert "secret" not in str(error.value)


@pytest.mark.parametrize("kind", ["missing", "probability", "wrong_type", "usage"])
async def test_invalid_answers_are_not_approvals(kind, snapshot):
    data = payload()
    if kind == "missing":
        del data["answers"]["fraud"]
    if kind == "probability":
        data["answers"]["fraud"]["noul"] = True
    if kind == "wrong_type":
        data["answers"]["fraud"]["type"] = "score"
    if kind == "usage":
        data["usage"]["requests_charged"] = -1
    async with httpx.AsyncClient(
        base_url="https://gateway.test/v1/",
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json=data)),
    ) as c:
        with pytest.raises(ClassifierUnavailable):
            await JevClassifier(c).classify(snapshot)


async def test_gateway_timeout(snapshot):
    def timeout(request):
        raise httpx.ReadTimeout("test", request=request)

    async with httpx.AsyncClient(
        base_url="https://gateway.test/v1/", transport=httpx.MockTransport(timeout)
    ) as c:
        with pytest.raises(ClassifierUnavailable):
            await JevClassifier(c).classify(snapshot)
