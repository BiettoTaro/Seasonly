from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.enums import Allergen, CountryCode, ProteinPreference
from app.db.session import get_db_session
from app.schemas.onboarding import (
    CountryReferenceResponse,
    CuisineReferenceResponse,
    EnumReferenceResponse,
)
from app.users.onboarding import list_countries_with_seasonal_data, list_cuisine_areas

router = APIRouter(prefix="/reference")


@router.get("/countries", response_model=list[CountryReferenceResponse])
async def read_countries(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[CountryReferenceResponse]:
    countries_with_data = await list_countries_with_seasonal_data(session)
    return [
        CountryReferenceResponse(
            code=country,
            name=country.name.replace("_", " ").title(),
            seasonal_data_available=country in countries_with_data,
            availability_message=(
                None if country in countries_with_data else "Seasonal data not available"
            ),
        )
        for country in CountryCode
    ]


@router.get("/cuisines", response_model=list[CuisineReferenceResponse])
async def read_cuisines(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[CuisineReferenceResponse]:
    return [CuisineReferenceResponse(area=area) for area in await list_cuisine_areas(session)]


@router.get("/allergens", response_model=list[EnumReferenceResponse])
async def read_allergens() -> list[EnumReferenceResponse]:
    return [_enum_response(allergen) for allergen in Allergen]


@router.get("/proteins", response_model=list[EnumReferenceResponse])
async def read_proteins() -> list[EnumReferenceResponse]:
    return [_enum_response(protein) for protein in ProteinPreference]


def _enum_response(value: Allergen | ProteinPreference) -> EnumReferenceResponse:
    return EnumReferenceResponse(value=value.value, label=value.value.replace("_", " ").title())
