from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from fastapi import APIRouter, Depends, HTTPException, Request
from src.application.ports.classifier import ClassifierUnavailable
from src.application.usecases.check_ad import CheckAd
from src.presentation.api.dependencies import check_ad_usecase
from src.presentation.api.schemas import CheckRequest, CheckResponse

router = APIRouter()


@router.post("/internal/checks", response_model=CheckResponse)
async def check_ad(
    body: CheckRequest, usecase: CheckAd = Depends(check_ad_usecase)
) -> CheckResponse:
    try:
        return CheckResponse.from_result(await usecase.execute(body.snapshot()))
    except ClassifierUnavailable:
        raise HTTPException(503, "Moderation is unavailable; retry later") from None


@router.get("/health")
async def health(request: Request) -> dict:
    try:
        async with request.app.state.session_factory() as session:
            await session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise HTTPException(503, "Database is unavailable") from None
    return {"status": "ok", "jev_configured": request.app.state.jev_configured}
