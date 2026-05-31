# Data Sources

Track candidate datasets here before importing them into the app.

Backend dataset registrations live in `backend/app/data/catalog.py`, with `DataKey` under `data_key/`, shared enums under `enums/`, and Pydantic data schemas under `schemas/`.

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

## Recipes

Initial backend key: `eu_recipes`.

## Recommendation Data

Initial backend key: `recommendation_events`.
