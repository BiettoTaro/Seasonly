from pydantic import BaseModel, ConfigDict, Field, HttpUrl
from typing import ClassVar

from app.data.data_key import DataKey
from app.data.enums import DataDomain
from app.data.schemas.target import DataTarget

class DataSourceMetadata(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(
        extra="forbid",
        from_attributes=True,
    )

    data_key: DataKey
    domain: DataDomain
    name: str = Field(min_length=1)
    region: str = Field(default="EU", min_length=1)
    source_url: HttpUrl | None = None
    licence: str | None = None
    update_frequency: str | None = None
    notes: str | None = None


class DataSourceRegistration(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(
        extra="forbid",
        from_attributes=True,
    )

    metadata: DataSourceMetadata
    targets: tuple[DataTarget, ...] = Field(min_length=1)
