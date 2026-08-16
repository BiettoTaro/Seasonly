# Recommendation robustness and cold-start evaluation

## Decision

Seasonly should integrate the deterministic seasonal TF-IDF ranker in Section 7 and retain
LightGBM LambdaRank as an offline prototype. LightGBM has slightly higher point NDCG@10, coverage
and diversity, but its relevance difference from TF-IDF is not distinguishable from zero on either
the locked test or the separate cold-start stress cohort.

This is a conservative engineering choice, not a real-user effectiveness conclusion. All outcomes
remain synthetic.

The planned private pilot of approximately 15–20 brief sessions is formative usability and system
testing, not model-effectiveness evaluation. Its consented events remain excluded from training and
metric claims under `docs/private-pilot-and-synthetic-ml.md`.

## Evaluation-only cold-start cohort

The approved stress design creates 1,000 deterministic `cold_start_newcomer` users over 30 dates,
from 25 July to 23 August 2026. Every user receives exactly one 20-recipe first-session slate:

- personal and user–recipe history features are fixed at zero;
- global recipe history is frozen from the source training split at 27 June 2026;
- the original 500 users and chronological train, validation and test splits are unchanged;
- stress user and slate identifiers are disjoint from the source dataset;
- the manifest prohibits fitting, tuning and early stopping;
- all candidates are rerun through seasonal, dietary and allergen hard filters.

The cohort has 20,000 candidate rows and 986 relevant slates. Forcing a first session guarantees
an evaluable candidate set but does not change the persona's within-session open, favourite or plan
probabilities.

## Metrics and uncertainty

NDCG@10 rewards highly relevant recipes near the top of a slate and normalises against that
slate's ideal order (Järvelin and Kekäläinen, 2002). Recall@10 measures the proportion of positive
candidates recovered in the first ten results. Coverage and ingredient diversity are retained as
separate measures because an NDCG gain does not imply a broader or more varied feed.

The evaluator calculates per-slate model differences and resamples those paired differences
10,000 times. Pairing is important because both rankers are judged on the same users, candidates
and outcomes. The reported percentile interval follows the bootstrap principle of estimating
sampling uncertainty by resampling observed units (Efron and Tibshirani, 1993).

| Cohort and model | NDCG@10 | Recall@10 | Catalogue coverage@10 | Ingredient diversity@10 |
|---|---:|---:|---:|---:|
| Locked test — popularity | 0.3487 | 0.5214 | 0.6667 | 0.9299 |
| Locked test — seasonal TF-IDF | 0.3655 | 0.5276 | 0.9029 | 0.9016 |
| Locked test — LightGBM | 0.3668 | 0.5273 | 0.9338 | 0.9168 |
| Cold start — popularity | 0.3266 | 0.5215 | 0.6071 | 0.9250 |
| Cold start — seasonal TF-IDF | 0.3313 | 0.5099 | 0.6865 | 0.9141 |
| Cold start — LightGBM | 0.3383 | 0.5163 | 0.7174 | 0.9142 |

The paired LightGBM-minus-TF-IDF results are:

| Cohort | Metric | Mean difference | 95% bootstrap interval | Positive resamples |
|---|---|---:|---:|---:|
| Locked test | NDCG@10 | +0.00124 | −0.00618 to +0.00856 | 63.18% |
| Locked test | Recall@10 | −0.00028 | −0.01002 to +0.00914 | 47.87% |
| Cold start | NDCG@10 | +0.00692 | −0.00712 to +0.02027 | 83.54% |
| Cold start | Recall@10 | +0.00648 | −0.01570 to +0.02811 | 71.84% |

Every interval crosses zero. LightGBM therefore fails the predefined gate requiring a positive
lower NDCG bound on both cohorts. The higher coverage and diversity are useful observations, but
they do not justify the additional trained-model dependency when relevance superiority is
uncertain.

## Slice findings

Slices with at least 30 relevant slates are marked eligible for interpretation; smaller slices are
retained in the machine-readable evidence but must not support a claim. These results are
descriptive and are not corrected for multiple comparisons.

The learned model's behaviour is mixed across personas. Its largest observed shortfall is for the
`low_engagement_browser` slice: −0.0340 NDCG@10 and −0.0658 Recall@10 relative to TF-IDF across 81
relevant slates. Other eligible persona differences are small and change direction. In cold start,
LightGBM's NDCG difference is +0.0003 for Germany, +0.0175 for France and +0.0030 for the United
Kingdom; these are descriptive point differences, not evidence of country-level superiority.

## Safety and coverage finding

The independent audit checks 314,986 source candidates and 20,000 cold-start candidates and finds
zero hard-filter violations. It also verifies that forbidden fields—persona, display position,
synthetic marker, generator version and outcome labels—do not overlap the 14 model features.

However, zero violations do not mean complete service:

- all 1,000 dedicated cold-start users receive a slate;
- only 427 of the original 500 users receive at least one slate;
- all 41 allergy-cautious users receive no candidates;
- only 9 of the original 41 low-activity cold-start users become active during the original
  simulation.

The allergy result is the expected consequence of the approved fail-closed policy: recipes with
unknown allergen assessments are excluded rather than treated as safe. It protects users but
reveals a catalogue-assessment coverage gap. This must remain a visible limitation and a future
data-quality task; the recommender must not weaken the safety rule to increase coverage.

## Reproducibility and notebook decision

The source dataset, stress dataset and model artifact are all linked by SHA-256 hashes. The native
LightGBM model is loaded without retraining, and its saved iteration count and ordered feature
schema are checked before prediction. LightGBM's supported Python API loads native artifacts with
`Booster(model_file=...)` and predicts with a selected iteration count (LightGBM developers, 2026).

Generate the isolated cohort:

```bash
./scripts/uv run python backend/scripts/generate_cold_start_stress_data.py
```

Run the ML evaluation:

```bash
./scripts/uv run --group ml python backend/scripts/evaluate_recommendation_robustness.py
```

The canonical result is
`datasets/synthetic/stress/cold-start-v1-seed-20260725/section6_evaluation-v2.json`.
Generated data is ignored by version control and existing evidence is never overwritten.

A Jupyter notebook is not required. The scripts are tested, typed and deterministic, making them
the source of truth. A later notebook may read the immutable JSON files to create dissertation
figures, but it should not contain separate preprocessing, training or evaluation logic.

## Section 6 acceptance gate

- Evaluation-only stress data is physically and logically separate: passed.
- Training and tuning are prohibited by manifest and code path: passed.
- Source and stress identifiers are disjoint: passed.
- Saved-model and input checksums are verified: passed.
- Personal history is zero and global history is frozen: passed.
- Forbidden outcome, persona and position features are absent: passed.
- Candidate safety audit has zero violations: passed.
- Allergy-persona service coverage: failed and recorded as a future catalogue-assessment task.
- LightGBM has a positive lower 95% NDCG difference on both cohorts: failed.
- Section 7 selection: seasonal TF-IDF, with hard filters applied before ranking.

## References

Efron, B. and Tibshirani, R.J. (1993) *An introduction to the bootstrap*. New York:
Chapman & Hall.

Järvelin, K. and Kekäläinen, J. (2002) ‘Cumulated gain-based evaluation of IR techniques’,
*ACM Transactions on Information Systems*, 20(4), pp. 422–446.
doi: 10.1145/582415.582418.

LightGBM developers (2026) *Python API: Booster*. Available at:
https://lightgbm.readthedocs.io/en/stable/pythonapi/lightgbm.Booster.html
(Accessed: 24 July 2026).
