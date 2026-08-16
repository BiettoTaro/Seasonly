from typing import cast

from sqlalchemy import Table

from app.models import RecommendationEvent


def test_recommendation_event_table_is_configured() -> None:
    table = cast(Table, RecommendationEvent.__table__)

    assert table.c.id.primary_key is True
    assert table.c.user_id.index is True
    assert table.c.recipe_id.index is True
    assert table.c.consent_id.index is True
    assert table.c.event_type.index is True
    assert table.c.slate_id.index is True
    assert table.c.occurred_at.index is True
    assert table.c.expires_at.index is True
    assert next(iter(table.c.user_id.foreign_keys)).ondelete == "CASCADE"
    assert next(iter(table.c.recipe_id.foreign_keys)).ondelete == "CASCADE"
    assert next(iter(table.c.consent_id.foreign_keys)).ondelete == "CASCADE"
    assert {constraint.name for constraint in table.constraints} >= {
        "ck_recommendation_events_event_type",
        "ck_recommendation_events_source",
        "ck_recommendation_events_position",
        "ck_recommendation_events_impression_slate",
        "ck_recommendation_events_expiry",
    }
