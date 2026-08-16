# Offline recommendation baselines

## Purpose

Seasonly uses two transparent baselines before training a learned ranking model. Their purpose is
to prove that the chronological preprocessing and evaluation pipeline behaves correctly and to set
a minimum result that a later model must exceed. The evaluation uses only synthetic interactions,
so it is engineering evidence rather than evidence of real-user satisfaction.

The version-2 dataset contains 20 candidates per recommendation slate. Each baseline reranks those
candidates and the evaluator measures its top 10. Dietary, allergen and seasonal eligibility are
applied before ranking and cannot be relaxed by either baseline.

## Baselines

### Weighted popularity

The popularity score is the sum of training-split relevance for each recipe, where an open,
favourite and plan have relevance 1, 2 and 3. Validation and test outcomes do not change the score.
An unseen recipe has a score of zero.

### Seasonal TF-IDF content

Each recipe is represented by prefixed name, cuisine area, category and ingredient tokens using an
L2-normalised TF-IDF vector. Scikit-learn defines TF-IDF as a document-term representation with
inverse-document-frequency weighting and supports L2 normalisation directly
(scikit-learn developers, 2026).

A user profile is the normalised, relevance-weighted sum of recipe vectors from that user's
positive training interactions. The final deterministic score is:

```text
0.60 × history similarity
+ 0.30 × seasonal_match_count / (seasonal_match_count + 1)
+ 0.10 × cuisine match
```

For a user without positive training history, the similarity component is zero; the baseline still
uses current seasonal strength and an explicit cuisine match. Synthetic persona identifiers and
display positions are never model inputs.

## Evaluation contract

- Models fit only the first 63 chronological days.
- Validation covers days 64–76 and test covers days 77–90.
- Candidates are grouped by their explicit `slate_id`.
- NDCG@10 and Recall@10 average only slates containing at least one positive outcome.
- Coverage and mean pairwise ingredient-Jaccard diversity use every slate.
- Zero-history results include relevant slates whose pre-slate impression count is exactly zero.
- Ties use recipe UUID order so repeated runs are deterministic.

NDCG rewards placing highly relevant results earlier while accounting for the ideal ranking for the
same query (Järvelin and Kekäläinen, 2002).

## Version-2 results

| Baseline | Split | NDCG@10 | Recall@10 | Catalogue coverage@10 | Ingredient diversity@10 |
|---|---:|---:|---:|---:|---:|
| Weighted popularity | Validation | 0.3450 | 0.5138 | 0.6623 | 0.9326 |
| Seasonal TF-IDF content | Validation | 0.3633 | 0.5237 | 0.9139 | 0.9028 |
| Weighted popularity | Test | 0.3487 | 0.5214 | 0.6667 | 0.9299 |
| Seasonal TF-IDF content | Test | 0.3655 | 0.5276 | 0.9029 | 0.9016 |

The content baseline improves test NDCG@10 by 0.0169, Recall@10 by 0.0062 and catalogue coverage by
0.2362 compared with popularity. Its ingredient diversity is 0.0283 lower, demonstrating that
relevance, coverage and diversity must remain separate acceptance criteria.

Only eight relevant zero-history slates occur in the test period. Popularity scores 0.3202 NDCG@10
and 0.5438 Recall@10 on this slice, while content scores 0.2300 and 0.4146. This sample is too small
to support model selection; it instead identifies cold start as a specific Section 5 design
requirement.

## Reproduction

After generating the version-2 dataset, run:

```bash
./scripts/uv run --group ml python backend/scripts/evaluate_recommendation_baselines.py
```

The evaluator verifies the input checksums and refuses to overwrite an existing result. Its output
is `baseline_metrics.json` beside the synthetic dataset.

## Limitations

The simulation outcomes are stochastic observations from the generating policy and retain position
bias. They cover only recipes that were displayed, so this is a reranking evaluation rather than a
complete-catalog retrieval evaluation. These results must not be reported as production
effectiveness or as proof of user benefit. Real consented interaction data and an appropriate
logged-policy evaluation design are required before a production claim can be made.

## References

Järvelin, K. and Kekäläinen, J. (2002) ‘Cumulated gain-based evaluation of IR techniques’,
*ACM Transactions on Information Systems*, 20(4), pp. 422–446. doi: 10.1145/582415.582418.

scikit-learn developers (2026) *TfidfVectorizer*. Available at:
https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html
(Accessed: 24 July 2026).
