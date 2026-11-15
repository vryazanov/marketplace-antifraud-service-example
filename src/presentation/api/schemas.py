from datetime import datetime

from pydantic import BaseModel, Field

from src.domain.entities import AdSnapshot, Category, CheckResult


class CheckRequest(BaseModel):
    ad_id: int = Field(gt=0)
    user_id: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1, max_length=20000)
    price: int = Field(ge=0)
    category: str = Field(min_length=1, max_length=100)
    city: str = Field(min_length=1, max_length=100)

    def snapshot(self) -> AdSnapshot:
        return AdSnapshot(**self.model_dump())


class CheckResponse(BaseModel):
    ad_id: int
    user_id: int
    content_hash: str
    policy_version: str
    status: str
    reason: str | None
    categories: list[Category]
    checked_at: datetime
    fraud_ads_in_week: int
    soft_delete_required: bool

    @classmethod
    def from_result(cls, result: CheckResult) -> "CheckResponse":
        a = result.assessment
        return cls(
            ad_id=a.ad_id,
            user_id=a.user_id,
            content_hash=a.content_hash,
            policy_version=a.policy_version,
            status="blocked" if a.decision.blocked else "allowed",
            reason=a.decision.reason,
            categories=list(a.decision.categories),
            checked_at=a.checked_at,
            fraud_ads_in_week=result.fraud_ads_in_week,
            soft_delete_required=result.soft_delete_required,
        )
