from fastapi import APIRouter

from app.data.catalog import get_data_targets, list_data_registrations
from app.data.data_key import DataKey
from app.data.schemas import DataSourceRegistration, DataTargetResponse

router = APIRouter(prefix="/data")


@router.get("/registrations", response_model=tuple[DataSourceRegistration, ...])
async def list_registrations() -> tuple[DataSourceRegistration, ...]:
    return list_data_registrations()


@router.get("/targets/{data_key}", response_model=DataTargetResponse)
async def read_targets(data_key: DataKey) -> DataTargetResponse:
    return DataTargetResponse(data_key=data_key, targets=get_data_targets(data_key))
