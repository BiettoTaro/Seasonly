import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.enums import CountryCode, Month, ProduceType
from app.models import Produce, ProduceSeason
from app.schemas.produce import SeasonalProduceGroupedResponse, SeasonalProduceResponse


async def list_seasonal_produce(
    session: AsyncSession,
    country_code: CountryCode,
    month: Month,
) -> SeasonalProduceGroupedResponse:
    result = await session.execute(
        select(
            Produce.id,
            Produce.name,
            Produce.type,
            Produce.mealdb_name,
            ProduceSeason.country_code,
            ProduceSeason.country_name,
            ProduceSeason.month,
            ProduceSeason.source_name,
            ProduceSeason.source_url,
        )
        .join(ProduceSeason, ProduceSeason.produce_id == Produce.id)
        .where(
            ProduceSeason.country_code == country_code.value,
            ProduceSeason.month == month.value,
        )
        .order_by(Produce.type, Produce.name)
    )
    produce = [_to_response(*row.tuple()) for row in result.all()]
    return SeasonalProduceGroupedResponse(
        fruits=[item for item in produce if item.type == ProduceType.FRUIT],
        vegetables=[item for item in produce if item.type == ProduceType.VEGETABLE],
    )


def _to_response(
    produce_id: uuid.UUID,
    name: str,
    produce_type: str,
    mealdb_name: str | None,
    country_code: str,
    country_name: str,
    month: int,
    source_name: str,
    source_url: str | None,
) -> SeasonalProduceResponse:
    return SeasonalProduceResponse(
        id=produce_id,
        name=name,
        type=ProduceType(produce_type),
        mealdb_name=mealdb_name,
        country_code=CountryCode(country_code),
        country_name=country_name,
        month=Month(month),
        source_name=source_name,
        source_url=source_url,
    )
