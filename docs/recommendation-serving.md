# Recommendation serving integration

## Selected architecture

Section 7 integrates the selected seasonal TF-IDF ranker directly into the existing FastAPI
monolith. It does not deploy the synthetic LightGBM artifact or synthetic user profiles.
Scikit-learn and NumPy are production dependencies; SciPy is installed through scikit-learn's
locked dependency graph. LightGBM remains in the optional `ml` dependency group and is absent from
the production image.

The endpoint is:

```text
GET /api/v1/me/recommendations/feed?month=7&limit=24
```

It requires authentication and returns:

- a server-issued random `slate_id`;
- country and month;
- ranking strategy `seasonal_tfidf_v1`;
- whether consented history or cuisine preference affected the order;
- the number of eligible candidates;
- up to 100 ranked recipe records.

The existing `GET /api/v1/recipes/seasonal` endpoint remains a browse and filtering endpoint.
Keeping browse and ranking separate prevents page-level SQL ordering or client-side merging from
silently changing the evaluated recommendation policy.

## Safety before ranking

The recommender cannot score an unsafe recipe because candidate eligibility is resolved first in
PostgreSQL:

1. recipe and provider must be active;
2. at least one ingredient must match produce in season for the profile country and requested
   month;
3. diet and explicit dietary-rule exclusions are applied;
4. every declared allergen must have a stored `does_not_contain` assessment.

Only the resulting candidate identifiers are passed to TF-IDF. Missing, `contains` and `unknown`
allergen assessments remain fail-closed. An empty safe set returns an empty feed rather than
weakening a filter.

## Content and ranking

The content index uses every active recipe's name, cuisine area, category and ingredients.
`TfidfVectorizer` learns the vocabulary and inverse-document-frequency values from the current
catalogue and L2-normalises recipe vectors. For L2-normalised vectors, the dot product is cosine
similarity (scikit-learn developers, 2026).

The shared offline and serving score is:

```text
0.60 × consented-history cosine similarity
+ 0.30 × seasonal_match_count / (seasonal_match_count + 1)
+ 0.10 × consented cuisine match
```

Scores are descending and exact ties use recipe UUID order. The shared
`recommendations/content_ranker.py` implementation is used by the offline baseline and production
feed. A byte-for-byte rerun of the frozen baseline output confirms that this refactor does not
change the Section 6 evidence.

The catalogue is currently small enough to build the in-memory index from current active records
for each request. This deliberately avoids stale-cache and invalidation behaviour in the first
serving version. Section 8 measures build latency without identifiers and provides an explicit
seasonal-only rollback. A future cache still requires a versioned refresh and rollback contract.

## Consent and user signals

Candidate safety uses the user's current diet, dietary rules and consented allergy profile
regardless of personalization status. Ranking reads recommendation history and cuisine preferences
only when the current personalization notice has active consent.

Without active personalization consent:

- the history query is not executed;
- cuisine preferences do not affect order;
- content similarity is zero;
- ranking is deterministic from current seasonal strength;
- the iOS client does not submit impressions.

With active consent, retained unexpired events produce a transparent recipe signal:

| Event | Weight |
|---|---:|
| Open | +1 |
| Favourite | +2 |
| Unfavourite | −2 |
| Plan | +3 |
| Unplan | −3 |

Weights aggregate per active recipe; a non-positive total is discarded. This allows removals to
undo state-based interest while repeated opens remain a weaker positive signal. Consent withdrawal
still deletes all identifiable recommendation events in the same transaction, so the next feed
uses cold-start ranking.

This production event aggregation is necessarily simpler than exact impression attribution because
existing action events are not linked to a prior slate. It is deterministic and auditable, but it
must be evaluated with real consented data before an effectiveness claim.

## iOS integration

The dashboard now requests the ranked feed once instead of fetching and merging one list per
preferred cuisine. When consent is active, the client records the displayed items with the
server-issued `slate_id`. Ordinary seasonal browsing no longer creates recommendation impressions.
The client contract has a decoding test for ranking metadata and recipe items.

## Verification

Section 7 verification includes:

- pure ranking tests for history similarity, cold start, tie-breaking and invalid signals;
- service tests proving safety arguments reach the eligibility query;
- a test proving no history read occurs without consent;
- route authentication, query and response-contract tests;
- a byte-for-byte frozen-baseline comparison;
- a read-only smoke request against the imported PostgreSQL catalogue;
- an iPhone 17 simulator build and unit-test run;
- a production Docker build and dependency import check.

The production image contains NumPy 2.5.1, SciPy 1.18.0 and scikit-learn 1.9.0, and excludes
LightGBM.

## Limitations

- Synthetic offline metrics are not evidence of real-user benefit.
- Allergy-cautious profiles can still receive an empty feed until verified
  `does_not_contain` assessments exist.
- The scorer is rebuilt per request; latency and catalogue-refresh monitoring belong to Section 8.
- The first serving version has no experimentation or automatic model promotion.
- The LightGBM artifact is not loaded by the API.

Operational mode switching, privacy-safe measurements and the future-model gate are documented in
`docs/recommendation-operations.md`.

## References

Järvelin, K. and Kekäläinen, J. (2002) ‘Cumulated gain-based evaluation of IR techniques’,
*ACM Transactions on Information Systems*, 20(4), pp. 422–446.
doi: 10.1145/582415.582418.

scikit-learn developers (2026) *TfidfVectorizer and cosine similarity*. Available at:
https://scikit-learn.org/stable/modules/feature_extraction.html#text-feature-extraction
(Accessed: 24 July 2026).
