from collections.abc import Awaitable
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db_session
from app.models import User
from app.schemas.onboarding import (
    AllergyUpdate,
    CuisineUpdate,
    DietaryRulesUpdate,
    DietUpdate,
    LocationUpdate,
    OnboardingProfileResponse,
    PrivacyAcknowledge,
    ProteinUpdate,
)
from app.users.onboarding import (
    IncompleteOnboardingError,
    InvalidOnboardingUpdateError,
    acknowledge_privacy,
    complete_onboarding,
    get_onboarding_profile,
    update_allergies,
    update_cuisines,
    update_diet,
    update_dietary_rules,
    update_location,
    update_proteins,
)

router = APIRouter(prefix="/me/onboarding")


@router.get("", response_model=OnboardingProfileResponse)
async def read_onboarding_profile(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> OnboardingProfileResponse:
    return await get_onboarding_profile(session, current_user)


@router.put("/privacy", response_model=OnboardingProfileResponse)
async def put_onboarding_privacy(
    payload: PrivacyAcknowledge,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> OnboardingProfileResponse:
    return await acknowledge_privacy(session, current_user, payload)


@router.put("/location", response_model=OnboardingProfileResponse)
async def put_onboarding_location(
    payload: LocationUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> OnboardingProfileResponse:
    return await update_location(session, current_user, payload)


@router.put("/diet", response_model=OnboardingProfileResponse)
async def put_onboarding_diet(
    payload: DietUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> OnboardingProfileResponse:
    return await _handle_update(session, update_diet(session, current_user, payload))


@router.put("/allergies", response_model=OnboardingProfileResponse)
async def put_onboarding_allergies(
    payload: AllergyUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> OnboardingProfileResponse:
    return await _handle_update(session, update_allergies(session, current_user, payload))


@router.put("/dietary-rules", response_model=OnboardingProfileResponse)
async def put_onboarding_dietary_rules(
    payload: DietaryRulesUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> OnboardingProfileResponse:
    return await _handle_update(session, update_dietary_rules(session, current_user, payload))


@router.put("/cuisines", response_model=OnboardingProfileResponse)
async def put_onboarding_cuisines(
    payload: CuisineUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> OnboardingProfileResponse:
    return await _handle_update(session, update_cuisines(session, current_user, payload))


@router.put("/proteins", response_model=OnboardingProfileResponse)
async def put_onboarding_proteins(
    payload: ProteinUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> OnboardingProfileResponse:
    return await _handle_update(session, update_proteins(session, current_user, payload))


@router.post("/complete", response_model=OnboardingProfileResponse)
async def post_onboarding_complete(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> OnboardingProfileResponse:
    try:
        return await complete_onboarding(session, current_user)
    except IncompleteOnboardingError as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"errors": e.errors},
        ) from e


async def _handle_update(
    session: AsyncSession,
    update: Awaitable[OnboardingProfileResponse],
) -> OnboardingProfileResponse:
    try:
        return await update
    except InvalidOnboardingUpdateError as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        ) from e
