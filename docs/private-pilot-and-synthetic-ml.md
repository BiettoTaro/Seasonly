# Private pilot and synthetic-only ML policy

## Decision

Seasonly cannot currently be distributed publicly because the EUFIC-derived seasonal dataset must
remain local until written redistribution permission or an openly licensed replacement is secured.
The available evaluation is therefore approximately 15–20 people using a privately supplied build
for a brief session.

These sessions are classified as formative usability and system testing. They are not a
representative recommendation dataset and must not be used to:

- train or tune a recommendation model;
- select features, weights or hyperparameters from observed tester outcomes;
- compare TF-IDF and LightGBM effectiveness;
- claim improvements in relevance, satisfaction or generalisation;
- set production alert thresholds.

This boundary reflects NIST's requirement to document data availability, representativeness and
suitability when planning AI evaluation, and to evaluate performance under conditions comparable
to deployment (National Institute of Standards and Technology, 2026). A small, brief convenience
sample does not meet that bar for model-effectiveness claims.

## Evidence classes

| Evidence | Permitted use | Prohibited interpretation |
|---|---|---|
| Deterministic synthetic personas | Pipeline tests, leakage checks, prototype training, regression comparison and safety-slice simulation | Real-user satisfaction or production benefit |
| Private tester observation | Navigation, comprehension, crashes, API failures, safety presentation and usability defects | Model fitting, ranking superiority or population-level conclusions |
| Privacy-safe feed measurements | Confirm instrumentation and inspect individual test failures | Production latency or empty-feed baselines |
| Consented recommendation events | Personalize that tester's feed under the current notice and retention rules | Current prototype training or effectiveness evaluation |

The offline loader already enforces the first boundary: it accepts only a manifest explicitly
classified as `synthetic`, with generator version and file checksum validation. Production
recommendation events and generated synthetic events use separate storage paths.

## Private-session protocol

Keep the reviewed `seasonal_tfidf_v1` policy active for every session. Do not A/B test LightGBM or
change ranking weights between participants.

Ask each tester to attempt the same core tasks:

1. create an account and complete the profile;
2. identify what the allergy and personalization consent controls mean;
3. find seasonal recommendations and understand unavailable-data states;
4. open, favourite and plan a recipe;
5. change a profile preference and observe the updated feed;
6. disable personalization and confirm the control remains understandable.

Record only the minimum evidence needed for the usability purpose:

- whether each task was completed;
- the point at which the tester became blocked or confused;
- the visible error or unexpected behaviour;
- concise tester feedback in their own words, if they agree to it;
- device and app-build version when needed to reproduce a defect.

Do not copy allergy details, credentials, access tokens, recommendation identifiers or database
records into observation notes. If screen recording or identifiable quotations are contemplated,
obtain the institutionally required agreement first; this runbook does not authorise them.
Human-centred evaluation throughout the interactive-system lifecycle is consistent with ISO
9241-210, but applicable institutional and human-participant requirements still take priority
(International Organization for Standardization, 2019).

## Consent and end-of-session handling

The personalization toggle remains optional. Refusing it must not prevent the tester from using
core recipe functionality. If a tester enabled personalization, disabling it at the end of the
session exercises the withdrawal flow and deletes that person's identifiable recommendation
events. If they leave it enabled, the existing 365-day maximum retention and daily expiry purge
continue to apply.

The profile screen provides password-reconfirmed JSON export and immediate account deletion.
Deletion cascades through user-owned application records and clears the iOS Keychain session. The
scope and deployment-level limitations are documented in `docs/privacy-controls.md`.

## ML and notebook decision

The deployed policy remains deterministic seasonal TF-IDF. LightGBM remains an offline synthetic
prototype because it did not pass the existing uncertainty gate and no suitable real dataset is
available.

A Jupyter notebook is still unnecessary for training. Tested scripts remain the canonical
generation, preprocessing, training and evaluation path. A notebook may read immutable output JSON
to produce dissertation figures, provided it contains no independent preprocessing or model logic.

## Re-entry gate for real-data ML

Real-event training should be reconsidered only after:

1. the seasonal-data licensing restriction is resolved for the intended distribution;
2. a sufficiently sustained deployment and intended user population are available;
3. the research or product purpose, lawful basis, notice and institutional requirements are
   reviewed;
4. participants understand whether their events may be used for model development;
5. sample-size and model-promotion criteria are agreed before examining outcomes;
6. the synthetic-only input guard is deliberately replaced by a versioned, audited real-data
   contract.

Until every gate is satisfied, synthetic evaluation can verify implementation behaviour but the
project must describe recommendation effectiveness as unvalidated with real users.

## References

International Organization for Standardization (2019) *ISO 9241-210:2019 Ergonomics of
human-system interaction — Part 210: Human-centred design for interactive systems*. Available at:
https://www.iso.org/standard/77520.html (Accessed: 24 July 2026).

National Institute of Standards and Technology (2026) *AI Risk Management Framework Core*.
Available at: https://airc.nist.gov/airmf-resources/airmf/5-sec-core/
(Accessed: 24 July 2026).
