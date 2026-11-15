from fastapi import Request
from src.application.usecases.check_ad import CheckAd
from src.infrastructure.persistence.uow import SQLAlchemyUnitOfWork


def check_ad_usecase(request: Request) -> CheckAd:
    return CheckAd(
        SQLAlchemyUnitOfWork(request.app.state.session_factory),
        request.app.state.classifier,
        request.app.state.policy,
    )
