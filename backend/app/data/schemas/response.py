from pydantic import BaseModel

from app.data.data_key import DataKey
from app.data.schemas.target import DataTarget


class DataTargetResponse(BaseModel):
    data_key: DataKey
    targets: tuple[DataTarget, ...]
