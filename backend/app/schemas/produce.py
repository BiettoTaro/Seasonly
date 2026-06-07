import uuid
from typing import ClassVar

from pydantic import BaseModel, ConfigDict

from app.data.enums import CountryCode, Month, ProduceType


class SeasonalProduceResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    type: ProduceType
    mealdb_name: str | None
    country_code: CountryCode
    country_name: str
    month: Month
    source_name: str
    source_url: str | None
