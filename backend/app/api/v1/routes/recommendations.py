import logging
from datetime import UTC, datetime
from time import perf_counter
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.config import settings
from app.data.enums import Month
from app.db.session import get_db_session
from app.models import User
from app.recommendations.events import (
    InvalidRecommendationImpressionError,
    PersonalizationConsentRequiredError,
    get_personalization_consent,
    grant_personalization_consent,
    record_recommendation_impressions,
    withdraw_personalization_consent,
)
from app.recommendations.feed import (
    RecommendationProfileError,
    build_recommendation_feed,
)
from app.recommendations.telemetry import RecommendationFeedMeasurement
from app.schemas.recommendation import (
    PersonalizationConsentResponse,
    PersonalizationConsentUpdate,
    RecommendationFeedResponse,
    RecommendationImpressionBatchCreate,
    RecommendationImpressionBatchResponse,
)

router = APIRouter(prefix="/me/recommendations")
logger = logging.getLogger(__name__)


@router.get("/feed", response_model=RecommendationFeedResponse)
async def read_recommendation_feed(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    month: Annotated[Month | None, Query(description="Defaults to the current UTC month")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 24,
) -> RecommendationFeedResponse:
    selected_month = month if month is not None else Month(datetime.now(UTC).month)
    started_at = perf_counter()
    try:
        feed = await build_recommendation_feed(
            session,
            user=current_user,
            month=selected_month,
            limit=limit,
            ranking_mode=settings.recommendation_ranking_mode,
        )
    except RecommendationProfileError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        ) from e
    measurement = RecommendationFeedMeasurement(
        ranking_strategy=feed.ranking_strategy,
        duration_ms=(perf_counter() - started_at) * 1000,
        eligible_count=feed.total,
        returned_count=len(feed.items),
        personalized=feed.personalized,
        empty_feed=not feed.items,
    )
    logger.info(measurement.to_json())
    return feed


@router.get("/consent", response_model=PersonalizationConsentResponse)
async def read_personalization_consent(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> PersonalizationConsentResponse:
    return await get_personalization_consent(session, user_id=current_user.id)


@router.put("/consent", response_model=PersonalizationConsentResponse)
async def save_personalization_consent(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    payload: PersonalizationConsentUpdate,
) -> PersonalizationConsentResponse:
    _ = payload
    return await grant_personalization_consent(session, user_id=current_user.id)


@router.delete("/consent", status_code=status.HTTP_204_NO_CONTENT)
async def delete_personalization_consent(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Response:
    await withdraw_personalization_consent(session, user_id=current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/impressions",
    response_model=RecommendationImpressionBatchResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def save_recommendation_impressions(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_user)],
    payload: RecommendationImpressionBatchCreate,
) -> RecommendationImpressionBatchResponse:
    try:
        received = await record_recommendation_impressions(
            session,
            user_id=current_user.id,
            payload=payload,
        )
    except PersonalizationConsentRequiredError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except InvalidRecommendationImpressionError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e
    return RecommendationImpressionBatchResponse(received=received)
