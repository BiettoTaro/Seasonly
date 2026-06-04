import builtins
from enum import StrEnum
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, field_serializer, model_validator

from app.data.enums import DataTargetType, StorageBackendType


class DataSpec(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    type: builtins.type[BaseModel]
    backend: StorageBackendType
    enable_memory_cache: bool = False

    @field_serializer("type")
    def serialize_type(self, value: builtins.type[BaseModel]) -> str:
        return value.__name__


class DataTarget(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    key: StrEnum | None = None
    spec: DataSpec | None = None
    target_type: DataTargetType | None = None
    name: str | None = Field(default=None, min_length=1)
    description: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def validate_target_shape(self) -> "DataTarget":
        has_spec_target = self.key is not None and self.spec is not None
        has_legacy_target = (
            self.target_type is not None and self.name is not None and self.description is not None
        )
        if has_spec_target or has_legacy_target:
            return self
        raise ValueError("DataTarget requires either key/spec or target_type/name/description")

    @field_serializer("key")
    def serialize_key(self, value: StrEnum | None) -> str | None:
        return value.value if value is not None else None
