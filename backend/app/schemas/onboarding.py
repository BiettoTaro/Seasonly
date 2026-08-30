import uuid
from datetime import datetime
from typing import Annotated, ClassVar, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.data.enums import (
    Allergen,
    AllergyProfileStatus,
    CountryCode,
    CuisinePreferenceStatus,
    DietaryRule,
    DietPattern,
    LocationSource,
    OnboardingStatus,
    OnboardingStep,
    ProteinPreference,
)

CURRENT_PRIVACY_NOTICE_VERSION = "2026-08-27"
CURRENT_TERMS_VERSION = "2026-08-27"
CURRENT_ALLERGY_CONSENT_VERSION = "2026-06-26"

RegionCode = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        to_upper=True,
        min_length=1,
        max_length=20,
        pattern=r"^[A-Z0-9][A-Z0-9_-]{0,19}$",
    ),
]


class PrivacyAcknowledge(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    acknowledged: bool
    terms_accepted: Literal[True]
    terms_version: Literal["2026-08-27"]

    @model_validator(mode="after")
    def require_acknowledgement(self) -> Self:
        if not self.acknowledged:
            raise ValueError("Privacy notice must be acknowledged.")
        return self


class LocationUpdate(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    country_code: CountryCode
    region_code: RegionCode | None = None
    source: LocationSource

    @field_validator("region_code", mode="before")
    @classmethod
    def normalize_region_code(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().upper()
        return value


class DietUpdate(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    diet_pattern: DietPattern


class AllergyUpdate(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    status: AllergyProfileStatus
    allergens: set[Allergen] = Field(default_factory=set, max_length=14)
    explicit_consent: bool = False

    @model_validator(mode="after")
    def validate_allergy_profile(self) -> Self:
        if self.status == AllergyProfileStatus.PROVIDED and not self.allergens:
            raise ValueError("At least one allergen is required when status is provided.")
        if self.status != AllergyProfileStatus.PROVIDED and self.allergens:
            raise ValueError("Allergens must be empty unless status is provided.")
        if self.status == AllergyProfileStatus.PROVIDED and not self.explicit_consent:
            raise ValueError("Explicit consent is required to store allergy information.")
        return self


class DietaryRulesUpdate(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    dietary_rules: set[DietaryRule] = Field(default_factory=set, max_length=4)


class CuisineUpdate(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    status: CuisinePreferenceStatus
    areas: list[str] = Field(default_factory=list, max_length=5)

    @field_validator("areas")
    @classmethod
    def normalize_areas(cls, value: list[str]) -> list[str]:
        normalized = [area.strip() for area in value]
        if any(not area or len(area) > 120 for area in normalized):
            raise ValueError("Cuisine areas must be between 1 and 120 characters.")
        if len({area.casefold() for area in normalized}) != len(normalized):
            raise ValueError("Cuisine areas must not contain duplicates.")
        return normalized

    @model_validator(mode="after")
    def validate_status(self) -> Self:
        if self.status == CuisinePreferenceStatus.PROVIDED and not self.areas:
            raise ValueError("At least one cuisine area is required when status is provided.")
        if self.status != CuisinePreferenceStatus.PROVIDED and self.areas:
            raise ValueError("Cuisine areas must be empty unless status is provided.")
        return self


class ProteinUpdate(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    proteins: list[ProteinPreference] = Field(default_factory=list, max_length=8)

    @field_validator("proteins")
    @classmethod
    def reject_duplicates(cls, value: list[ProteinPreference]) -> list[ProteinPreference]:
        if len(set(value)) != len(value):
            raise ValueError("Protein preferences must not contain duplicates.")
        return value


class OnboardingProfileResponse(BaseModel):
    status: OnboardingStatus
    next_step: OnboardingStep
    user_id: uuid.UUID
    country_code: CountryCode | None
    region_code: str | None
    location_source: LocationSource | None
    privacy_notice_version: str | None
    privacy_notice_acknowledged_at: datetime | None
    diet_pattern: DietPattern | None
    allergy_status: AllergyProfileStatus
    allergens: list[Allergen]
    dietary_rules: list[DietaryRule]
    cuisine_preference_status: CuisinePreferenceStatus
    cuisine_areas: list[str]
    proteins: list[ProteinPreference]
    completed_at: datetime | None
    updated_at: datetime | None


class OnboardingCompletionErrorResponse(BaseModel):
    errors: list[str]


class CountryReferenceResponse(BaseModel):
    code: CountryCode
    name: str
    seasonal_data_available: bool
    availability_message: str | None = None


class CuisineReferenceResponse(BaseModel):
    area: str


class EnumReferenceResponse(BaseModel):
    value: str
    label: str
