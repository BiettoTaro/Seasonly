from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.enums import CountryCode, Month
from app.db.session import get_db_session
from app.produce.service import list_seasonal_produce
from app.schemas.produce import SeasonalProduceGroupedResponse

router = APIRouter(prefix="/produce")


@router.get("/seasonal", response_model=SeasonalProduceGroupedResponse)
async def read_seasonal_produce(
    country: Annotated[CountryCode, Query(description="ISO 3166-1 alpha-2 country code")],
    month: Annotated[Month, Query(description="Calendar month number from 1 to 12")],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SeasonalProduceGroupedResponse:
    return await list_seasonal_produce(session, country, month)
