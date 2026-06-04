import uuid
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field


class UserProfileResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    display_name: str | None = Field(default=None, max_length=100)
    country_code: str | None = Field(default=None, min_length=2, max_length=2)
    region_code: str | None = Field(default=None, max_length=20)
    location_source: str | None = Field(default=None, max_length=30)
