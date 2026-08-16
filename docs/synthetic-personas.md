# Synthetic recommendation personas

## Scope

Seasonly defines 12 adult persona archetypes and deterministically distributes 500 generated users
across them. The personas vary by country, diet, cuisine affinity, engagement, planning behaviour,
variety preference and cold-start status. One persona has a declared peanut allergy so the
fail-closed allergen path remains part of every simulation.

The default simulation covers 90 chronological days from 26 April 2026, uses seed `20260724`, and
displays up to 20 actual Seasonly recipe candidates per active session. It generates impressions,
opens, favourites, unfavourites, plans and unplans.

## Safety and provenance boundaries

- Recipes are loaded from the imported PostgreSQL catalog. The generator does not invent recipe
  identifiers.
- Seasonal eligibility uses the same produce-to-recipe mapping as the application.
- Dietary exclusions reuse the application rules.
- A persona with an allergy can see a recipe only when the relevant assessment is explicitly
  `does_not_contain`. Unknown assessments remain ineligible.
- Every generated user, event and training example is marked synthetic.
- Persona identifiers are retained for analysis but explicitly excluded from model features,
  because a real user will not have a synthetic persona label.
- Generated interactions never enter the production `recommendation_events` table.

## Preprocessing

Each impression becomes one ranking example. Opens, favourites and plans are attributed to the
latest matching impression within 24 hours and produce relevance levels 1, 2 and 3 respectively.
Historical counts are calculated before the current event, preventing future information from
entering the feature row.

Every generated feed has a deterministic UUID `slate_id`. All candidates displayed together share
that identifier, and user-history features are snapshotted before the slate. Position remains
available for presentation-bias analysis but is excluded from model features because it is assigned
after ranking.

The 90-day timeline is divided chronologically:

- days 1–63: training;
- days 64–76: validation;
- days 77–90: testing.

An outcome is not attached across a split boundary. This prevents a validation action from
changing a training label.

Synthetic test scores show whether the implementation learns the simulation rules. They must not
be described as evidence of real-user satisfaction, generalisation or production effectiveness.

## Generation

After applying migrations and importing both seasonal and TheMealDB data, run:

```bash
./scripts/uv run python backend/scripts/generate_synthetic_recommendation_data.py
```

Each run is published atomically to a new directory under `datasets/synthetic/runs/`. Existing runs
are never overwritten. The output contains:

- `personas.csv`;
- `users.csv`;
- `recipes.csv`;
- `events.csv`;
- `training_examples.csv`;
- `manifest.json`, including parameters, counts and SHA-256 checksums.

The generation and preprocessing pipeline is executable application code rather than a notebook.
A Jupyter notebook may be added later for model exploration and dissertation visualisations, but
it must call the tested pipeline instead of duplicating preprocessing logic.
