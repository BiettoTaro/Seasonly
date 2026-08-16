# Recommendation operations and promotion controls

## Scope

This runbook covers the production recommendation policy added in Sections 7 and 8. It provides:

- one validated runtime switch between the reviewed TF-IDF policy and a seasonal-only rollback;
- privacy-minimised measurements for each successfully built feed;
- a manual promotion gate for any future learned model.

The switch does not relax recipe, diet or allergen eligibility. Both modes receive only candidates
that passed the same PostgreSQL safety filter.

## Runtime modes

`RECOMMENDATION_RANKING_MODE` accepts exactly:

| Value | Behaviour |
|---|---|
| `seasonal_tfidf_v1` | Reviewed default. Uses TF-IDF, seasonal strength and consented signals. |
| `seasonal_only_v1` | Emergency rollback. Uses seasonal strength and UUID tie-breaking only. |

The default is `seasonal_tfidf_v1`. Pydantic Settings reads environment variables into typed
settings, and an unsupported enum value fails validation rather than silently selecting another
policy (Pydantic, 2026). The rollback mode deliberately does not read personalization consent,
recommendation history, recipe content vectors or cuisine preferences.

## Privacy-safe measurements

Each successful feed build emits one JSON log object at `INFO` level:

```json
{"duration_ms":12.345,"eligible_count":40,"empty_feed":false,"event":"recommendation_feed_built","personalized":true,"ranking_strategy":"seasonal_tfidf_v1","returned_count":24}
```

The contract permits only:

- duration in milliseconds;
- eligible and returned counts;
- empty-feed state;
- whether consented inputs changed ranking;
- active ranking strategy;
- the fixed event name.

It excludes user, recipe, slate, country, IP, authentication and free-text fields. This minimises
the information processed for operational monitoring, consistent with the UK GDPR requirement to
limit personal data to what is necessary for a stated purpose (Information Commissioner's Office,
2026). Logs must remain subject to the deployment platform's access controls and retention policy;
the application does not create a second analytics store.

The current service does not define automatic alert thresholds. Synthetic traffic is not an
evidence-based latency or empty-feed baseline. After at least seven representative days of real
traffic, the operator should calculate p50 and p95 duration plus empty-feed rate by strategy, then
record reviewed thresholds before enabling alerts. Until then, these fields support manual
inspection only.

## Rollback procedure

1. Set `RECOMMENDATION_RANKING_MODE=seasonal_only_v1` in the API deployment environment.
2. Restart or redeploy the API so settings are reconstructed and validated.
3. Request an authenticated feed and confirm `ranking_strategy` is `seasonal_only_v1`.
4. Confirm the service logs a `recommendation_feed_built` record with the same strategy.
5. Check that eligibility and empty-feed behaviour remain plausible; never loosen safety filters
   to increase the count.

To restore the reviewed policy, set the value to `seasonal_tfidf_v1`, restart the API, and repeat
steps 3–5. An invalid value prevents application startup; there is no silent fallback.

## Future model promotion gate

The synthetic LightGBM experiment remains offline and is not a production option. A future model
must not be added to the runtime enum or loaded by the API until all of the following are recorded:

1. a versioned dataset contract using only appropriately consented and retained interactions;
2. the unchanged fail-closed safety filter before scoring;
3. chronological train, validation and test splits with leakage checks;
4. comparison against the frozen seasonal and TF-IDF baselines, including cold-start and safety
   slices;
5. a pre-agreed benefit threshold and uncertainty method based on real data;
6. reproducible training dependencies, parameters, seed and an integrity hash for the artifact;
7. API, rollback, privacy and production-image tests;
8. manual review and an explicit new enum value with its own rollback path.

There is no automatic training, hot reload, experiment assignment or model promotion. This follows
the testing, evaluation, verification and validation emphasis of the NIST AI Risk Management
Framework resources (National Institute of Standards and Technology, 2026). A model that fails any
gate remains offline.

The current 15–20-person brief private pilot is explicitly outside this promotion gate: it is
formative usability testing and its events must not be used to satisfy real-data evidence
requirements. See `docs/private-pilot-and-synthetic-ml.md`.

## Verification evidence

Section 8 tests establish that:

- both reviewed environment values construct valid settings and an unknown value is rejected;
- rollback retains profile safety arguments and skips every personalization/content read;
- rollback ordering is deterministic;
- the response reports the active mode;
- the emitted JSON object has an exact allow-list of privacy-safe fields.

The full backend test, Ruff, basedpyright and production-container checks must pass before this
section is complete.

## References

Information Commissioner's Office (2026) *Principle (c): Data minimisation*. Available at:
https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/data-protection-principles/a-guide-to-the-data-protection-principles/data-minimisation/
(Accessed: 24 July 2026).

National Institute of Standards and Technology (2026) *NIST AI Resource Center*. Available at:
https://airc.nist.gov/ (Accessed: 24 July 2026).

Pydantic (2026) *Settings management*. Available at:
https://docs.pydantic.dev/latest/concepts/pydantic_settings/ (Accessed: 24 July 2026).
