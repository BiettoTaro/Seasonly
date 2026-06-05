import uuid
from datetime import datetime
from typing import ClassVar, Self

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class UserProfileBase(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    country_code: str | None = Field(default=None, min_length=2, max_length=2)
    region_code: str | None = Field(default=None, min_length=1, max_length=20)
    location_source: str | None = Field(default=None, min_length=1, max_length=30)

    @model_validator(mode="after")
    def normalize_codes(self) -> Self:
        if self.country_code is not None:
            self.country_code = self.country_code.upper()
        if self.region_code is not None:
            self.region_code = self.region_code.upper()
        return self


class UserProfileCreate(UserProfileBase):
    pass


class UserProfileUpdate(UserProfileBase):
    pass


class UserProfileResponse(UserProfileBase):
    model_config: ClassVar[ConfigDict] = ConfigDict(from_attributes=True)

    user_id: uuid.UUID


class UserCreate(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    profile: UserProfileCreate | None = None


class UserUpdate(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)
    profile: UserProfileUpdate | None = None


class UserResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime
    profile: UserProfileResponse | None = None
