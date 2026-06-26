import uuid
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field

from app.data.enums import CountryCode, Month


class SeasonalRecipeResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    category: str | None
    area: str | None
    country_of_origin: str | None
    thumbnail_url: str | None
    matched_seasonal_produce: list[str]
    matched_seasonal_produce_count: int


class SeasonalRecipeListResponse(BaseModel):
    country_code: CountryCode
    month: Month
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total: int = Field(ge=0)
    items: list[SeasonalRecipeResponse]
