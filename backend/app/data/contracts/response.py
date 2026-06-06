from typing import ClassVar

from pydantic import BaseModel, ConfigDict

from app.data.contracts.target import DataTarget
from app.data.data_key import DataKey


class DataTargetResponse(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    data_key: DataKey
    targets: tuple[DataTarget, ...]
