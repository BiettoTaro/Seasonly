from pydantic import BaseModel, ConfigDict, Field

from app.data.enums import DataTargetType


class DataTarget(BaseModel):
    model_config = ConfigDict(frozen=True)

    target_type: DataTargetType
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
