# Recommendation safety and readiness

## Current policy

Recipe allergen handling is fail-closed. Each recipe has one assessment for each of the 14
configured allergens and each assessment has one of three states:

- `contains`: a deterministic rule found a known allergen term.
- `does_not_contain`: a reviewed source or manual assessment verified absence.
- `unknown`: absence has not been verified.

When a user declares an allergy, a recipe is eligible only when every declared allergen has a
stored `does_not_contain` assessment. A missing, `contains`, or `unknown` assessment excludes the
recipe. The initial migration deliberately backfills `unknown`; the deterministic importer can
confirm `contains`, but it never interprets a missing keyword as proof of safety.

This means allergy-aware recommendations can be empty until a reviewed allergen dataset or manual
review process supplies verified `does_not_contain` assessments. Substitution suggestions and
machine-learned allergen inference are deferred because they must not be presented as safety
guarantees.

## Country availability

The country reference endpoint derives availability from rows in `produce_seasons`. Countries
without data remain in the reference list and database enum, but the iOS picker displays them in a
disabled, secondary style with `Seasonal data not available`. Device and locale detection also
avoid selecting an unavailable country.

## Readiness audit

After migrations and data imports, run:

```bash
./scripts/uv run python backend/scripts/audit_recommendation_readiness.py
```

The read-only JSON report includes:

- active and seasonally matchable recipe counts;
- produce-to-TheMealDB ingredient mapping coverage;
- month and produce coverage for every configured country;
- expected, stored, and missing allergen assessments grouped by status and method.

The report intentionally supplies measurements rather than inventing pass thresholds. Acceptance
thresholds should be agreed before model training.
