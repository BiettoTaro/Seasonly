import uuid
from datetime import datetime
from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CurrentPasswordRequest(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    current_password: str = Field(min_length=8, max_length=128)


class AccountDeletionRequest(CurrentPasswordRequest):
    confirmation: Literal["DELETE"]


class UserDataExportAccount(BaseModel):
    id: uuid.UUID
    email: EmailStr
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime
    terms_version: str | None = None
    terms_accepted_at: datetime | None = None


class RankedPreferenceExport(BaseModel):
    value: str
    preference_rank: int | None


class UserDataExportProfile(BaseModel):
    display_name: str | None
    country_code: str | None
    region_code: str | None
    location_source: str | None
    onboarding_status: str
    privacy_notice_version: str | None
    privacy_notice_acknowledged_at: datetime | None
    diet_pattern: str | None
    allergy_status: str
    allergens: list[str]
    allergy_updated_at: datetime | None
    dietary_rules: list[str]
    dietary_rules_updated_at: datetime | None
    cuisine_preference_status: str
    cuisine_preferences: list[RankedPreferenceExport]
    protein_preferences: list[RankedPreferenceExport]
    completed_at: datetime | None
    updated_at: datetime


class ConsentExport(BaseModel):
    id: uuid.UUID
    consent_type: str
    notice_version: str
    granted_at: datetime
    withdrawn_at: datetime | None


class FavouriteExport(BaseModel):
    recipe_id: uuid.UUID
    recipe_name: str
    created_at: datetime


class RecipeHistoryExport(BaseModel):
    recipe_id: uuid.UUID
    recipe_name: str
    viewed_at: datetime


class PlannedMealExport(BaseModel):
    id: uuid.UUID
    recipe_id: uuid.UUID
    recipe_name: str
    day_of_week: int
    meal_slot: str
    created_at: datetime


class RecommendationEventExport(BaseModel):
    id: uuid.UUID
    recipe_id: uuid.UUID
    consent_id: uuid.UUID
    event_type: str
    source: str
    slate_id: uuid.UUID | None
    position: int | None
    occurred_at: datetime
    expires_at: datetime


class RefreshSessionExport(BaseModel):
    id: uuid.UUID
    family_id: uuid.UUID
    parent_token_id: uuid.UUID | None
    created_at: datetime
    expires_at: datetime
    revoked_at: datetime | None


class PasswordResetRequestExport(BaseModel):
    id: uuid.UUID
    created_at: datetime
    expires_at: datetime
    used_at: datetime | None


class UserDataExportSecurityRecords(BaseModel):
    refresh_sessions: list[RefreshSessionExport]
    password_reset_requests: list[PasswordResetRequestExport]


class UserDataExportRecipeActivity(BaseModel):
    favourites: list[FavouriteExport]
    history: list[RecipeHistoryExport]
    planned_meals: list[PlannedMealExport]


class UserDataExport(BaseModel):
    format_version: Literal["seasonly-user-data-v1"]
    exported_at: datetime
    account: UserDataExportAccount
    profile: UserDataExportProfile | None
    consents: list[ConsentExport]
    recipe_activity: UserDataExportRecipeActivity
    recommendation_events: list[RecommendationEventExport]
    security_records: UserDataExportSecurityRecords
