# Data Sources

Track candidate datasets here before importing them into the app.

Backend dataset registrations live in `backend/app/data/registry.py`, with `DataKey` under
`data_key/`, shared enums under `enums/`, and data contracts under `contracts/`.

For each source, record:

- Dataset name.
- URL.
- Region coverage.
- Licence.
- Update frequency.
- Data format.
- Fields relevant to Seasonly.
- Import notes.

## Seasonal Produce

Initial backend key: `eu_seasonal_produce`.

### EUFIC Seasonal Fruit and Vegetables Tool

- Source: [Explore Seasonal Fruit and Vegetables in Europe](https://www.eufic.org/en/explore-seasonal-fruit-and-vegetables-in-europe)
- Supporting references: [European national sources](https://www.eufic.org/en/page/european-national-sources-to-find-information-on-seasonal-fruit-and-vegetables)
- Terms: [EUFIC terms of use](https://www.eufic.org/en/using-this-site/terms-of-use)
- Coverage: European countries exposed by the tool; Seasonly extracts EU-27 countries plus the
  United Kingdom.
- Format: JavaScript data rendered by an interactive web tool.
- Refresh frequency: Not stated.
- Licence and redistribution: EUFIC's terms allow use and dissemination only under conditions
  including non-commercial use, no modification, and attribution. A normalized CSV is modified
  material, so the full extracted dataset is not redistributed in this repository.
- Provenance: EUFIC states that the tool combines various European national sources. The source
  lists may not be comprehensive and may vary by climate and location.
- Usage: Treat the data as best available seasonal guidance, not absolute truth. Full raw and
  processed extracts are stored locally in gitignored directories for non-commercial academic
  prototyping only.
- Release requirement: Obtain written permission from EUFIC or replace this source with an openly
  licensed dataset before public or commercial release.

The committed `datasets/samples/seasonal_sample.csv` contains synthetic demonstration rows and is
not extracted from EUFIC.

## Recipes

Backend key: `themealdb_recipes`.

### TheMealDB

- Source: [TheMealDB API](https://www.themealdb.com/api.php)
- Terms: [TheMealDB terms of use](https://www.themealdb.com/terms_of_use.php)
- Coverage: International recipes, with area and country metadata where available.
- Format: JSON API.
- Refresh frequency: Not stated; a latest-meals endpoint is available to paid API users.
- Licence and attribution: API content can be copied and modified through official endpoints. Paid
  usage requires TheMealDB attribution and compliance with its rate limit and third-party content
  terms.
- Import notes and proposed PostgreSQL model: [TheMealDB API exploration](mealdb-api.md)

## Recommendation Data

Initial backend key: `recommendation_events`.

Consent-gated production events are stored in PostgreSQL and documented in
[`recommendation-events.md`](recommendation-events.md). Deterministic synthetic personas are a
separate development source documented in [`synthetic-personas.md`](synthetic-personas.md).
Synthetic interactions are restricted to pipeline tests, prototype training and clearly labelled
demonstrations; they are not real-user evaluation data. Brief private-pilot events are likewise
excluded from current ML training and effectiveness claims under
[`private-pilot-and-synthetic-ml.md`](private-pilot-and-synthetic-ml.md).
