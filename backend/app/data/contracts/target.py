from typing import ClassVar

from pydantic import BaseModel, ConfigDict, field_serializer

from app.data.enums import DataTargetType, StorageBackendType

type PydanticModelType = type[BaseModel]


class DataSpec(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    type: PydanticModelType
    backend: StorageBackendType
    enable_memory_cache: bool = False

    @field_serializer("type")
    def serialize_type(self, value: PydanticModelType) -> str:
        return value.__name__


class DataTarget(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    key: str | None = None
    spec: DataSpec | None = None
    target_type: DataTargetType | None = None
    name: str | None = None
    description: str | None = None
