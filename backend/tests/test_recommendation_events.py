import uuid
from datetime import UTC, datetime, timedelta
from typing import cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.enums import RecommendationEventSource, RecommendationEventType
from app.models import RecommendationEvent, UserConsent
from app.recommendations import events as recommendation_events
from app.schemas.recommendation import (
    RecommendationImpressionBatchCreate,
    RecommendationImpressionCreate,
)


class AddOnlySession:
    def __init__(self) -> None:
        self.added: list[object] = []

    def add(self, value: object) -> None:
        self.added.append(value)


class ScalarValues:
    def __init__(self, values: list[uuid.UUID]) -> None:
        self.values: list[uuid.UUID] = values

    def all(self) -> list[uuid.UUID]:
        return self.values


class ExecuteResult:
    def __init__(self, values: list[uuid.UUID]) -> None:
        self.values: list[uuid.UUID] = values

    def scalars(self) -> ScalarValues:
        return ScalarValues(self.values)


class ImpressionSession:
    def __init__(self, active_recipe_ids: list[uuid.UUID]) -> None:
        self.active_recipe_ids: list[uuid.UUID] = active_recipe_ids
        self.execute_count: int = 0
        self.committed: bool = False

    async def execute(self, statement: object) -> ExecuteResult:
        _ = statement
        self.execute_count += 1
        if self.execute_count == 1:
            return ExecuteResult(self.active_recipe_ids)
        return ExecuteResult([])

    async def commit(self) -> None:
        self.committed = True


async def no_active_consent(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    lock_for_update: bool = False,
) -> UserConsent | None:
    _ = session, user_id, lock_for_update
    return None


def active_consent(user_id: uuid.UUID) -> UserConsent:
    return UserConsent(
        id=uuid.UUID("00000000-0000-0000-0000-000000000003"),
        user_id=user_id,
        consent_type="personalization",
        notice_version="2026-07-24",
        granted_at=datetime(2026, 7, 24, tzinfo=UTC),
    )


@pytest.mark.asyncio
async def test_action_event_is_not_stored_without_consent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = AddOnlySession()
    monkeypatch.setattr(
        recommendation_events,
        "_active_personalization_consent",
        no_active_consent,
    )

    recorded = await recommendation_events.record_recommendation_event_if_consented(
        cast(AsyncSession, cast(object, session)),
        user_id=uuid.uuid4(),
        recipe_id=uuid.uuid4(),
        event_type=RecommendationEventType.OPEN,
        source=RecommendationEventSource.RECIPE_DETAIL,
    )

    assert recorded is False
    assert session.added == []


@pytest.mark.asyncio
async def test_action_event_expires_after_365_days(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = AddOnlySession()
    user_id = uuid.uuid4()
    consent = active_consent(user_id)
    occurred_at = datetime(2026, 7, 24, 12, tzinfo=UTC)

    async def override_active_consent(
        session: AsyncSession,
        *,
        user_id: uuid.UUID,
        lock_for_update: bool = False,
    ) -> UserConsent | None:
        _ = session, user_id
        assert lock_for_update is True
        return consent

    monkeypatch.setattr(
        recommendation_events,
        "_active_personalization_consent",
        override_active_consent,
    )

    recorded = await recommendation_events.record_recommendation_event_if_consented(
        cast(AsyncSession, cast(object, session)),
        user_id=user_id,
        recipe_id=uuid.uuid4(),
        event_type=RecommendationEventType.FAVOURITE,
        source=RecommendationEventSource.RECIPE_DETAIL,
        now=occurred_at,
    )

    assert recorded is True
    assert len(session.added) == 1
    event = cast(RecommendationEvent, session.added[0])
    assert event.consent_id == consent.id
    assert event.occurred_at == occurred_at
    assert event.expires_at == occurred_at + timedelta(days=365)


@pytest.mark.asyncio
async def test_action_event_locks_consent_until_the_caller_commits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = AddOnlySession()
    user_id = uuid.uuid4()
    consent = active_consent(user_id)
    lock_requests: list[bool] = []

    async def override_active_consent(
        session: AsyncSession,
        *,
        user_id: uuid.UUID,
        lock_for_update: bool = False,
    ) -> UserConsent | None:
        _ = session, user_id
        lock_requests.append(lock_for_update)
        return consent

    monkeypatch.setattr(
        recommendation_events,
        "_active_personalization_consent",
        override_active_consent,
    )

    recorded = await recommendation_events.record_recommendation_event_if_consented(
        cast(AsyncSession, cast(object, session)),
        user_id=user_id,
        recipe_id=uuid.uuid4(),
        event_type=RecommendationEventType.OPEN,
        source=RecommendationEventSource.RECIPE_DETAIL,
    )

    assert recorded is True
    assert lock_requests == [True]


@pytest.mark.asyncio
async def test_impressions_lock_consent_until_the_batch_commits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user_id = uuid.uuid4()
    recipe_id = uuid.uuid4()
    session = ImpressionSession([recipe_id])
    consent = active_consent(user_id)
    lock_requests: list[bool] = []

    async def override_active_consent(
        session: AsyncSession,
        *,
        user_id: uuid.UUID,
        lock_for_update: bool = False,
    ) -> UserConsent | None:
        _ = session, user_id
        lock_requests.append(lock_for_update)
        return consent

    monkeypatch.setattr(
        recommendation_events,
        "_active_personalization_consent",
        override_active_consent,
    )
    payload = RecommendationImpressionBatchCreate(
        slate_id=uuid.uuid4(),
        impressions=[
            RecommendationImpressionCreate(
                event_id=uuid.uuid4(),
                recipe_id=recipe_id,
                position=1,
            )
        ],
    )

    received = await recommendation_events.record_recommendation_impressions(
        cast(AsyncSession, cast(object, session)),
        user_id=user_id,
        payload=payload,
    )

    assert received == 1
    assert lock_requests == [True]
    assert session.committed is True
