import pytest

from app.recommendations.evaluation import paired_bootstrap_interval


def test_paired_bootstrap_is_deterministic() -> None:
    first = paired_bootstrap_interval(
        [0.1, -0.05, 0.2, 0.0],
        iterations=2_000,
        seed=42,
    )
    second = paired_bootstrap_interval(
        [0.1, -0.05, 0.2, 0.0],
        iterations=2_000,
        seed=42,
    )

    assert first == second
    expected_mean = 0.0625
    tolerance = max(1e-6 * abs(expected_mean), 1e-12)
    assert abs(expected_mean - first.mean_delta) <= tolerance


def test_paired_bootstrap_detects_uniformly_positive_difference() -> None:
    result = paired_bootstrap_interval(
        [0.1, 0.2, 0.3, 0.4],
        iterations=2_000,
        seed=42,
    )

    assert result.lower_95 > 0
    assert result.probability_positive == 1.0


def test_paired_bootstrap_requires_sufficient_iterations() -> None:
    with pytest.raises(ValueError, match="at least 1,000"):
        _ = paired_bootstrap_interval(
            [0.1],
            iterations=999,
            seed=42,
        )
