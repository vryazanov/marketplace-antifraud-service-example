from contextlib import asynccontextmanager

import httpx
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from fastapi import FastAPI
from src.domain.entities import Policy
from src.infrastructure.jev.client import JevClassifier, UnconfiguredClassifier
from src.infrastructure.jev.questions import PROMPT_VERSION
from src.presentation.api.routes.internal import router
from src.settings import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        engine = create_async_engine(settings.async_database_url(), pool_pre_ping=True)
        key = settings.lms_llm_api_key.get_secret_value()
        async with httpx.AsyncClient(
            base_url=settings.jev_base_url.rstrip("/") + "/",
            headers={"x-api-key": key},
            timeout=settings.jev_timeout_seconds,
            follow_redirects=False,
        ) as client:
            app.state.session_factory = async_sessionmaker(
                engine, expire_on_commit=False
            )
            app.state.classifier = (
                JevClassifier(client) if key else UnconfiguredClassifier()
            )
            app.state.jev_configured = bool(key)
            app.state.policy = Policy(settings.antifraud_threshold, PROMPT_VERSION)
            try:
                yield
            finally:
                await engine.dispose()

    app = FastAPI(title="Antifraud Service", lifespan=lifespan)
    app.include_router(router)
    return app
