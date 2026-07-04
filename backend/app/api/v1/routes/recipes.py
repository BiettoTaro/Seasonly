from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.data.enums import (
    Allergen,
    AllergyProfileStatus,
    CountryCode,
    DietaryRule,
    DietPattern,
    Month,
)
from app.db.session import get_db_session
from app.models import User
from app.recipes.service import list_seasonal_recipes
from app.schemas.recipe import SeasonalRecipeListResponse

router = APIRouter(prefix="/recipes")


@router.get("/seasonal", response_model=SeasonalRecipeListResponse)
async def read_seasonal_recipes(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    month: Annotated[Month | None, Query(description="Defaults to the current UTC month")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    category: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
    area: Annotated[str | None, Query(min_length=1, max_length=120)] = None,
    origin: Annotated[str | None, Query(min_length=1, max_length=120)] = None,
) -> SeasonalRecipeListResponse:
    country_code = _profile_country_code(current_user)
    selected_month = month if month is not None else Month(datetime.now(UTC).month)
    return await list_seasonal_recipes(
        session,
        country_code=country_code,
        month=selected_month,
        page=page,
        page_size=page_size,
        category=category,
        area=area,
        country_of_origin=origin,
        excluded_allergens=_profile_allergens(current_user),
        diet_pattern=_profile_diet(current_user),
        dietary_rules=_profile_dietary_rules(current_user),
    )


def _profile_country_code(user: User) -> CountryCode:
    if user.profile is None or user.profile.country_code is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="A supported profile country is required for seasonal recipes",
        )
    try:
        return CountryCode(user.profile.country_code)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="A supported profile country is required for seasonal recipes",
        ) from error


def _profile_allergens(user: User) -> set[Allergen]:
    if (
        user.profile is None
        or user.profile.allergy_status != AllergyProfileStatus.PROVIDED.value
    ):
        return set()
    return {Allergen(item.allergen) for item in user.profile.allergens}


def _profile_diet(user: User) -> DietPattern | None:
    if user.profile is None or user.profile.diet_pattern is None:
        return None
    return DietPattern(user.profile.diet_pattern)


def _profile_dietary_rules(user: User) -> set[DietaryRule]:
    if user.profile is None:
        return set()
    return {DietaryRule(item.dietary_rule) for item in user.profile.dietary_rules}
