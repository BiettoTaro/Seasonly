# Backend

FastAPI monolith for Seasonly.

## Current Scope

- App settings through `pydantic-settings`.
- Health endpoint.
- Versioned API router.
- Data catalog with modular `data_key`, `enums`, `data_target`, and `data/schemas` packages.
- Placeholder domain packages for auth, users, produce, recipes, and recommendations.

Database migrations, persistence models, and authentication implementation are intentionally left as next-step decisions.
