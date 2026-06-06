from typing import ClassVar

from pydantic import BaseModel, ConfigDict

from app.data.contracts.target import DataTarget
from app.data.data_key import DataKey
from app.data.enums import DataDomain


class DataSourceMetadata(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    data_key: DataKey
    name: str
    domain: DataDomain
    notes: str | None = None


class DataSourceRegistration(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    metadata: DataSourceMetadata
    targets: tuple[DataTarget, ...]
