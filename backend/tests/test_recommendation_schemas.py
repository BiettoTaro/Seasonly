import uuid

import pytest
from pydantic import ValidationError

from app.schemas.recommendation import (
    PersonalizationConsentUpdate,
    RecommendationImpressionBatchCreate,
)


def test_personalization_consent_requires_affirmative_opt_in() -> None:
    with pytest.raises(ValidationError, match="Explicit consent is required"):
        _ = PersonalizationConsentUpdate(explicit_consent=False)


def test_impression_batch_rejects_invalid_position() -> None:
    with pytest.raises(ValidationError):
        _ = RecommendationImpressionBatchCreate.model_validate(
            {
                "slate_id": str(uuid.uuid4()),
                "impressions": [
                    {
                        "event_id": str(uuid.uuid4()),
                        "recipe_id": str(uuid.uuid4()),
                        "position": 0,
                    }
                ],
            }
        )


def test_impression_batch_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        _ = RecommendationImpressionBatchCreate.model_validate(
            {
                "slate_id": str(uuid.uuid4()),
                "impressions": [
                    {
                        "event_id": str(uuid.uuid4()),
                        "recipe_id": str(uuid.uuid4()),
                        "position": 1,
                        "allergy": "peanuts",
                    }
                ],
            }
        )


def test_impression_batch_requires_slate_identifier() -> None:
    with pytest.raises(ValidationError, match="slate_id"):
        _ = RecommendationImpressionBatchCreate.model_validate(
            {
                "impressions": [
                    {
                        "event_id": str(uuid.uuid4()),
                        "recipe_id": str(uuid.uuid4()),
                        "position": 1,
                    }
                ]
            }
        )
