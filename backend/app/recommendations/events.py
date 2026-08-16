import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.enums import (
    ConsentType,
    RecommendationEventSource,
    RecommendationEventType,
)
from app.models import Recipe, RecommendationEvent, UserConsent, UserProfile
from app.schemas.recommendation import (
    CURRENT_PERSONALIZATION_CONSENT_VERSION,
    RECOMMENDATION_EVENT_RETENTION_DAYS,
    PersonalizationConsentResponse,
    RecommendationImpressionBatchCreate,
)


class PersonalizationConsentRequiredError(PermissionError):
    pass


class InvalidRecommendationImpressionError(ValueError):
    pass


async def get_personalization_consent(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> PersonalizationConsentResponse:
    consent = await _active_personalization_consent(session, user_id=user_id)
    return _consent_response(consent)


async def personalization_consent_is_active(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> bool:
    return await _active_personalization_consent(session, user_id=user_id) is not None


async def grant_personalization_consent(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> PersonalizationConsentResponse:
    profile = await session.get(UserProfile, user_id)
    if profile is None:
        session.add(UserProfile(user_id=user_id))
        await session.flush()

    consent = await _active_personalization_consent(session, user_id=user_id)
    if consent is None:
        await _withdraw_outdated_personalization_consents(session, user_id=user_id)
        consent = UserConsent(
            user_id=user_id,
            consent_type=ConsentType.PERSONALIZATION.value,
            notice_version=CURRENT_PERSONALIZATION_CONSENT_VERSION,
        )
        session.add(consent)
        await session.commit()
        await session.refresh(consent)
    return _consent_response(consent)


async def withdraw_personalization_consent(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> None:
    withdrawn_at = _utc_now()
    _ = await session.execute(
        update(UserConsent)
        .where(
            UserConsent.user_id == user_id,
            UserConsent.consent_type == ConsentType.PERSONALIZATION.value,
            UserConsent.withdrawn_at.is_(None),
        )
        .values(withdrawn_at=withdrawn_at)
    )
    _ = await session.execute(
        delete(RecommendationEvent).where(RecommendationEvent.user_id == user_id)
    )
    await session.commit()


async def record_recommendation_event_if_consented(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    recipe_id: uuid.UUID,
    event_type: RecommendationEventType,
    source: RecommendationEventSource,
    position: int | None = None,
    now: datetime | None = None,
) -> bool:
    consent = await _active_personalization_consent(
        session,
        user_id=user_id,
        lock_for_update=True,
    )
    if consent is None:
        return False
    occurred_at = now or _utc_now()
    session.add(
        RecommendationEvent(
            user_id=user_id,
            recipe_id=recipe_id,
            consent_id=consent.id,
            event_type=event_type.value,
            source=source.value,
            position=position,
            occurred_at=occurred_at,
            expires_at=occurred_at + timedelta(days=RECOMMENDATION_EVENT_RETENTION_DAYS),
        )
    )
    return True


async def record_recommendation_impressions(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    payload: RecommendationImpressionBatchCreate,
    now: datetime | None = None,
) -> int:
    consent = await _active_personalization_consent(
        session,
        user_id=user_id,
        lock_for_update=True,
    )
    if consent is None:
        raise PersonalizationConsentRequiredError(
            "Personalization consent is required to record recommendation events."
        )

    recipe_ids = {impression.recipe_id for impression in payload.impressions}
    result = await session.execute(
        select(Recipe.id).where(
            Recipe.id.in_(recipe_ids),
            Recipe.is_active.is_(True),
        )
    )
    active_recipe_ids = set(result.scalars().all())
    missing_recipe_ids = recipe_ids - active_recipe_ids
    if missing_recipe_ids:
        raise InvalidRecommendationImpressionError(
            "Impressions contain unknown or inactive recipes."
        )

    occurred_at = now or _utc_now()
    expires_at = occurred_at + timedelta(days=RECOMMENDATION_EVENT_RETENTION_DAYS)
    statement = insert(RecommendationEvent).values(
        [
            {
                "id": impression.event_id,
                "user_id": user_id,
                "recipe_id": impression.recipe_id,
                "consent_id": consent.id,
                "event_type": RecommendationEventType.IMPRESSION.value,
                "source": RecommendationEventSource.SEASONAL_FEED.value,
                "slate_id": payload.slate_id,
                "position": impression.position,
                "occurred_at": occurred_at,
                "expires_at": expires_at,
            }
            for impression in payload.impressions
        ]
    )
    statement = statement.on_conflict_do_nothing(index_elements=[RecommendationEvent.id])
    _ = await session.execute(statement)
    await session.commit()
    return len(payload.impressions)


async def purge_expired_recommendation_events(
    session: AsyncSession,
    *,
    now: datetime | None = None,
) -> int:
    result = await session.execute(
        delete(RecommendationEvent)
        .where(RecommendationEvent.expires_at <= (now or _utc_now()))
        .returning(RecommendationEvent.id)
    )
    deleted_count = len(result.scalars().all())
    await session.commit()
    return deleted_count


async def _active_personalization_consent(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    lock_for_update: bool = False,
) -> UserConsent | None:
    statement = (
        select(UserConsent)
        .where(
            UserConsent.user_id == user_id,
            UserConsent.consent_type == ConsentType.PERSONALIZATION.value,
            UserConsent.notice_version == CURRENT_PERSONALIZATION_CONSENT_VERSION,
            UserConsent.withdrawn_at.is_(None),
        )
        .order_by(UserConsent.granted_at.desc())
        .limit(1)
    )
    if lock_for_update:
        statement = statement.with_for_update()
    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def _withdraw_outdated_personalization_consents(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> None:
    _ = await session.execute(
        update(UserConsent)
        .where(
            UserConsent.user_id == user_id,
            UserConsent.consent_type == ConsentType.PERSONALIZATION.value,
            UserConsent.notice_version != CURRENT_PERSONALIZATION_CONSENT_VERSION,
            UserConsent.withdrawn_at.is_(None),
        )
        .values(withdrawn_at=_utc_now())
    )


def _consent_response(
    consent: UserConsent | None,
) -> PersonalizationConsentResponse:
    return PersonalizationConsentResponse(
        active=consent is not None,
        notice_version=CURRENT_PERSONALIZATION_CONSENT_VERSION,
        granted_at=consent.granted_at if consent is not None else None,
        retention_days=RECOMMENDATION_EVENT_RETENTION_DAYS,
    )


def _utc_now() -> datetime:
    return datetime.now(UTC)
