import uuid

import numpy as np
import pytest

from app.recommendations.offline_data import ModelTrainingExample
from app.recommendations.preprocessing import MODEL_FEATURE_COLUMNS, DatasetSplit
from app.recommendations.ranker import (
    CATEGORICAL_FEATURE_COLUMNS,
    UNKNOWN_CATEGORY_CODE,
    FeatureEncoder,
    RankerConfig,
    encode_split,
    train_ranker,
)


def model_example(
    sequence: int,
    *,
    split: DatasetSplit,
    slate_sequence: int,
    relevance: int,
    country: str = "GB",
    prior_impressions: int = 20,
) -> ModelTrainingExample:
    return ModelTrainingExample(
        slate_id=uuid.UUID(f"10000000-0000-0000-0000-{slate_sequence:012d}"),
        user_id=uuid.UUID("20000000-0000-0000-0000-000000000001"),
        recipe_id=uuid.UUID(f"30000000-0000-0000-0000-{sequence:012d}"),
        split=split,
        persona_key="synthetic_test_persona",
        relevance=relevance,
        month=7,
        seasonal_match_count=(sequence % 4) + 1,
        cuisine_match=sequence % 2,
        user_country=country,
        user_diet="omnivore",
        recipe_area="British" if sequence % 2 else "Italian",
        recipe_category="Main",
        user_prior_impressions=prior_impressions,
        user_prior_opens=5,
        user_prior_favourites=2,
        user_prior_plans=1,
        user_recipe_prior_impressions=sequence % 3,
        recipe_prior_impressions=100 + sequence,
        recipe_prior_positive_actions=20 + relevance,
    )


def test_feature_encoder_is_fitted_on_training_categories_only() -> None:
    training = [
        model_example(
            1,
            split=DatasetSplit.TRAIN,
            slate_sequence=1,
            relevance=1,
        )
    ]
    encoder = FeatureEncoder.fit(training)
    unseen = model_example(
        2,
        split=DatasetSplit.TEST,
        slate_sequence=2,
        relevance=0,
        country="FR",
    )

    matrix = encoder.transform([unseen])
    country_index = MODEL_FEATURE_COLUMNS.index("user_country")

    assert matrix[0, country_index] == UNKNOWN_CATEGORY_CODE
    assert set(encoder.category_mappings) == set(CATEGORICAL_FEATURE_COLUMNS)
    assert "persona_key" not in MODEL_FEATURE_COLUMNS
    assert "position" not in MODEL_FEATURE_COLUMNS


def test_feature_encoder_rejects_non_training_fit_rows() -> None:
    with pytest.raises(ValueError, match="training examples only"):
        _ = FeatureEncoder.fit(
            [
                model_example(
                    1,
                    split=DatasetSplit.VALIDATION,
                    slate_sequence=1,
                    relevance=1,
                )
            ]
        )


def test_feature_encoder_round_trips_its_strict_json_contract() -> None:
    training = [
        model_example(
            1,
            split=DatasetSplit.TRAIN,
            slate_sequence=1,
            relevance=1,
        )
    ]
    fitted = FeatureEncoder.fit(training)

    loaded = FeatureEncoder.from_json(fitted.as_json())

    assert loaded == fitted


def test_feature_encoder_rejects_changed_feature_order() -> None:
    training = [
        model_example(
            1,
            split=DatasetSplit.TRAIN,
            slate_sequence=1,
            relevance=1,
        )
    ]
    payload = FeatureEncoder.fit(training).as_json()
    payload["feature_columns"] = list(reversed(MODEL_FEATURE_COLUMNS))

    with pytest.raises(ValueError, match="does not match"):
        _ = FeatureEncoder.from_json(payload)


def test_encoded_split_preserves_query_groups_and_history_snapshot() -> None:
    examples = [
        model_example(
            sequence,
            split=DatasetSplit.TRAIN,
            slate_sequence=slate,
            relevance=sequence % 4,
            prior_impressions=slate * 10,
        )
        for slate in (1, 2)
        for sequence in range((slate - 1) * 4 + 1, slate * 4 + 1)
    ]
    encoder = FeatureEncoder.fit(examples)

    encoded = encode_split(
        examples=examples,
        split=DatasetSplit.TRAIN,
        encoder=encoder,
    )

    assert encoded.features.shape == (8, len(MODEL_FEATURE_COLUMNS))
    assert encoded.labels.shape == (8,)
    assert encoded.group_sizes.tolist() == [4, 4]
    assert int(encoded.group_sizes.sum()) == len(encoded.examples)


def test_lightgbm_ranker_training_is_deterministic_on_grouped_data() -> None:
    training = [
        model_example(
            sequence=(slate * 10) + position,
            split=DatasetSplit.TRAIN,
            slate_sequence=slate,
            relevance=3 if position == 1 else position % 2,
            prior_impressions=slate * 10,
        )
        for slate in range(1, 5)
        for position in range(1, 5)
    ]
    validation = [
        model_example(
            sequence=(slate * 10) + position,
            split=DatasetSplit.VALIDATION,
            slate_sequence=slate,
            relevance=3 if position == 1 else position % 2,
            prior_impressions=slate * 10,
        )
        for slate in range(5, 7)
        for position in range(1, 5)
    ]
    encoder = FeatureEncoder.fit(training)
    encoded_training = encode_split(
        examples=training,
        split=DatasetSplit.TRAIN,
        encoder=encoder,
    )
    encoded_validation = encode_split(
        examples=validation,
        split=DatasetSplit.VALIDATION,
        encoder=encoder,
    )
    config = RankerConfig(
        name="unit_test",
        num_leaves=3,
        min_child_samples=1,
        reg_lambda=1.0,
    )

    first = train_ranker(
        training=encoded_training,
        validation=encoded_validation,
        config=config,
    )
    second = train_ranker(
        training=encoded_training,
        validation=encoded_validation,
        config=config,
    )

    assert first.best_iteration == second.best_iteration
    assert np.array_equal(
        first.predict(encoded_validation),
        second.predict(encoded_validation),
    )
