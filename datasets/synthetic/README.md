# Synthetic recommendation datasets

Run outputs in this directory are generated from deterministic adult personas and the actual
Seasonly recipe catalog. They are ignored by version control because they can be regenerated from
their manifest, seed and source database.

Synthetic interactions are suitable for pipeline tests, prototype-model training and dissertation
demonstrations. They are not evidence of real-user recommendation effectiveness and must never be
merged into the production `recommendation_events` table.

Versioned run directories may also contain `baseline_metrics.json`. This file is derived only from
the checksummed synthetic CSV files, records the source manifest hash, and carries the same
evaluation restriction.

The `stress/` namespace contains evaluation-only cohorts. Their manifests must set both
`training_prohibited` and `tuning_prohibited` to `true`; these rows may never be appended to a
training, validation or early-stopping split. Section 6 cold-start runs contain one forced
first-session slate per synthetic newcomer, with personal history fixed at zero and recipe history
frozen at the source training cutoff.
