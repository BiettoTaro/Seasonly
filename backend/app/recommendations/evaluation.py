# pyright: reportMissingTypeStubs=false

from collections.abc import Sequence
from dataclasses import dataclass
from typing import cast

import numpy as np


@dataclass(frozen=True)
class BootstrapInterval:
    samples: int
    iterations: int
    seed: int
    mean_delta: float
    lower_95: float
    upper_95: float
    probability_positive: float


def paired_bootstrap_interval(
    deltas: Sequence[float],
    *,
    iterations: int,
    seed: int,
) -> BootstrapInterval:
    if not deltas:
        raise ValueError("Paired bootstrap requires at least one paired result")
    if iterations < 1_000:
        raise ValueError("Paired bootstrap requires at least 1,000 iterations")

    values = np.asarray(deltas, dtype=np.float64)
    rng = np.random.default_rng(seed)
    sample_indices = rng.integers(
        low=0,
        high=len(values),
        size=(iterations, len(values)),
    )
    bootstrap_means = np.mean(values[sample_indices], axis=1)
    raw_bounds = cast(
        object,
        np.quantile(bootstrap_means, [0.025, 0.975]),
    )
    bounds = np.asarray(raw_bounds, dtype=np.float64)
    bound_values = cast(list[float], bounds.tolist())
    return BootstrapInterval(
        samples=len(values),
        iterations=iterations,
        seed=seed,
        mean_delta=float(np.mean(values)),
        lower_95=bound_values[0],
        upper_95=bound_values[1],
        probability_positive=float(np.mean(bootstrap_means > 0)),
    )
