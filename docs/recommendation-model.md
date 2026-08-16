# LightGBM recommendation ranker

## Decision and scope

Seasonly's first learned recommendation candidate is a LightGBM LambdaRank model. LambdaRank is
appropriate because training examples are grouped into recommendation slates and the objective is
the order of recipes within each slate rather than an independent classification decision
(Burges, 2010). LightGBM provides efficient gradient-boosted decision trees and a ranking-specific
Python estimator that accepts query-group sizes for training and validation (Ke *et al.*, 2017;
LightGBM developers, 2026).

This artifact is a synthetic prototype. It is not approved as evidence of production
effectiveness and is not yet connected to the API.

## Data and safety boundary

- Training uses version-2 synthetic data generated from actual Seasonly recipe records.
- Days 1–63 are used for fitting.
- Days 64–76 are used for early stopping and configuration selection.
- Days 77–90 are evaluated once after configuration selection.
- Every ranking group is an explicit `slate_id`.
- Synthetic persona identifiers and display positions are excluded.
- Categorical vocabularies are fitted only on the training split.
- A category not present during fitting receives LightGBM's missing-category value `-1`; it is
  never guessed to be another category.
- Dietary, allergen and seasonal eligibility remain hard pre-ranking filters. The model cannot
  reintroduce an excluded recipe.

## Features

The 14 model features are:

- month, seasonal match count and cuisine match;
- user country and diet;
- recipe area and category;
- prior user impressions, opens, favourites and plans;
- prior user–recipe impressions;
- prior recipe impressions and positive actions.

All historical values are captured before the current slate. This prevents candidates displayed
together from changing one another's history features.

## Controlled search

Four predefined configurations vary tree leaves, minimum child samples and L2 regularisation. All
use:

- `objective="lambdarank"`;
- NDCG@10 validation;
- relevance gains `[0, 1, 3, 7]`;
- learning rate 0.05 and a maximum of 500 rounds;
- 30-round early stopping;
- seed `20260724`;
- one CPU thread, deterministic mode and forced column-wise training.

LightGBM notes that deterministic CPU mode should be combined with forced row-wise or column-wise
training, although exact reproducibility can still depend on the library, compiler and platform
(LightGBM developers, 2026).

The selected configuration has 31 leaves, a minimum of 250 examples per child and L2
regularisation 1.0. Early stopping selected iteration 21.

## Results

| Model | Test NDCG@10 | Test Recall@10 | Catalogue coverage@10 | Ingredient diversity@10 |
|---|---:|---:|---:|---:|
| Weighted popularity | 0.3487 | 0.5214 | 0.6667 | 0.9299 |
| Seasonal TF-IDF | 0.3655 | 0.5276 | 0.9029 | 0.9016 |
| LightGBM LambdaRank | 0.3668 | 0.5273 | 0.9338 | 0.9168 |

Compared with TF-IDF, LambdaRank improves test NDCG@10 by 0.0012, catalogue coverage by 0.0309 and
ingredient diversity by 0.0152, while Recall@10 decreases by 0.0003. Section 6's paired bootstrap
found that this relevance difference is not statistically supported: its 95% interval is
−0.0062 to 0.0086. The model therefore remains an offline prototype rather than the Section 7
integration choice.

Only eight relevant zero-history test slates are present. LambdaRank scores 0.2305 NDCG@10 and
0.4667 Recall@10 on that slice. The separate 1,000-user cold-start stress cohort also found an
uncertain difference from TF-IDF. Full evidence and the resulting decision gate are recorded in
`docs/recommendation-evaluation.md`.

Gain importance is highest for cuisine match, recipe area, recipe history and recipe category.
These values describe how this fitted synthetic model split its trees; they are not causal
explanations of user preference.

## Artifact contract

The generated artifact contains:

- `model.txt`: LightGBM's native text model;
- `feature_schema.json`: ordered features and training-only category mappings;
- `tuning_results.json`: validation results for every candidate, explicitly excluding test scores;
- `manifest.json`: selected configuration, one-time test result, limitations, library versions and
  SHA-256 checksums.

The saved model loads independently as 21 trees with 14 features. Generated artifact directories
are ignored by version control and are never overwritten.

## Reproduction

```bash
./scripts/uv run --group ml python backend/scripts/train_recommendation_ranker.py
```

Preprocessing, tuning and packaging are tested application code. A Jupyter notebook is not
required for training; a later dissertation notebook may read the immutable manifests to make
figures without duplicating model logic.

## References

Burges, C.J.C. (2010) *From RankNet to LambdaRank to LambdaMART: An overview*. Microsoft Research
Technical Report MSR-TR-2010-82.

Ke, G., Meng, Q., Finley, T., Wang, T., Chen, W., Ma, W., Ye, Q. and Liu, T.-Y. (2017)
‘LightGBM: A highly efficient gradient boosting decision tree’, *Advances in Neural Information
Processing Systems*, 30.

LightGBM developers (2026) *LightGBM Python API: LGBMRanker*. Available at:
https://lightgbm.readthedocs.io/en/stable/pythonapi/lightgbm.LGBMRanker.html
(Accessed: 24 July 2026).
