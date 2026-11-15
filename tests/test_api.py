from contextlib import asynccontextmanager

import httpx

from src.application.ports.classifier import ClassifierUnavailable
from src.application.usecases.check_ad import CheckAd
from src.domain.entities import Category, Policy
from src.fastapi import create_app
from src.presentation.api.dependencies import check_ad_usecase
from src.settings import Settings
from tests.conftest import FakeClassifier
from tests.test_usecase import MemoryUow


async def test_blocked_response_explains_reason(snapshot):
    app = create_app(Settings(lms_llm_api_key=""))
    app.dependency_overrides[check_ad_usecase] = lambda: CheckAd(
        MemoryUow(), FakeClassifier((Category.THREATS,)), Policy()
    )
    async with client_for(app) as c:
        r = await c.post("/internal/checks", json=snapshot.__dict__)
    assert r.status_code == 200
    assert r.json()["status"] == "blocked" and r.json()["reason"]
    assert not r.json()["soft_delete_required"]


async def test_unavailable_api_never_leaks_key_or_approves(snapshot):
    class Unavailable(FakeClassifier):
        async def classify(self, snapshot):
            raise ClassifierUnavailable("secret-value")

    app = create_app(Settings(lms_llm_api_key=""))
    app.dependency_overrides[check_ad_usecase] = lambda: CheckAd(
        MemoryUow(), Unavailable(), Policy()
    )
    async with client_for(app) as c:
        r = await c.post("/internal/checks", json=snapshot.__dict__)
    assert r.status_code == 503 and "secret-value" not in r.text
    assert "allowed" not in r.text


async def test_invalid_snapshot_does_not_reach_classifier(snapshot):
    classifier = FakeClassifier()
    app = create_app(Settings(lms_llm_api_key=""))
    app.dependency_overrides[check_ad_usecase] = lambda: CheckAd(
        MemoryUow(), classifier, Policy()
    )
    async with client_for(app) as c:
        r = await c.post("/internal/checks", json={**snapshot.__dict__, "price": -1})
    assert r.status_code == 422 and classifier.calls == 0


@asynccontextmanager
async def client_for(app):
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            yield client
