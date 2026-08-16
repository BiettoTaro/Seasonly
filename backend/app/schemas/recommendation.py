import uuid
from datetime import datetime
from typing import ClassVar, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.data.enums import CountryCode, Month, RecommendationRankingStrategy
from app.schemas.recipe import SeasonalRecipeResponse

CURRENT_PERSONALIZATION_CONSENT_VERSION = "2026-07-24"
RECOMMENDATION_EVENT_RETENTION_DAYS = 365


class PersonalizationConsentUpdate(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    explicit_consent: bool

    @model_validator(mode="after")
    def require_explicit_consent(self) -> Self:
        if not self.explicit_consent:
            raise ValueError("Explicit consent is required to enable personalization.")
        return self


class PersonalizationConsentResponse(BaseModel):
    active: bool
    notice_version: str
    granted_at: datetime | None
    retention_days: int


class RecommendationImpressionCreate(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    event_id: uuid.UUID
    recipe_id: uuid.UUID
    position: int = Field(ge=1, le=100)


class RecommendationImpressionBatchCreate(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    slate_id: uuid.UUID
    impressions: list[RecommendationImpressionCreate] = Field(
        min_length=1,
        max_length=100,
    )


class RecommendationImpressionBatchResponse(BaseModel):
    received: int


class RecommendationFeedResponse(BaseModel):
    slate_id: uuid.UUID
    country_code: CountryCode
    month: Month
    ranking_strategy: RecommendationRankingStrategy
    personalized: bool
    total: int = Field(ge=0)
    items: list[SeasonalRecipeResponse]
