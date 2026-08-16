# Backend

FastAPI monolith for Seasonly.

## Current Scope

- App settings through `pydantic-settings`.
- Health endpoint.
- Versioned API router.
- User registration, login token, and authenticated self-service user CRUD endpoints.
- Alembic migrations for database schema lifecycle.
- Data registry with modular `data_key`, `data_source`, `data_target`, and `data/contracts` packages.
- Placeholder domain packages for produce, recipes, and recommendations.

## Database Migrations

Apply migrations after PostgreSQL is running:

```bash
./scripts/uv run alembic upgrade head
```

Render migration SQL without connecting to the database:

```bash
./scripts/uv run alembic upgrade head --sql
```

## Seasonal Produce Data

The API reads seasonal produce only from PostgreSQL. Generate and import the local EUFIC-derived
dataset with:

```bash
./scripts/uv run python backend/scripts/scrape_eufic_seasonal.py
./scripts/uv run alembic upgrade head
./scripts/uv run python backend/scripts/import_seasonal_data.py
```

Query imported records with:

```bash
curl "http://localhost:8001/api/v1/produce/seasonal?country=GB&month=6"
```

## Recipe Data

Apply migrations and import a complete TheMealDB snapshot with:

```bash
./scripts/uv run alembic upgrade head
./scripts/uv run python backend/scripts/import_mealdb_recipes.py
```

The importer fetches and validates the complete provider snapshot before changing recipe tables.
Recipe persistence is transactional, while a separate `data_import_runs` record retains success or
failure status and imported record counts. Missing recipes are not immediately deactivated because
a single provider scan can be incomplete; deactivation requires a separate repeated-miss policy.

Authenticated users can list recipes matching produce seasonal in their profile country:

```bash
curl "http://localhost:8001/api/v1/recipes/seasonal?month=6&category=Vegetarian" \
  -H "Authorization: Bearer <token>"
```

The profile country applies only to seasonal produce matching. Recipe `origin` is an independent,
optional filter.

Allergy-aware recommendations are fail-closed: recipes are returned only when every allergen
declared by the user has a verified `does_not_contain` assessment. Unknown or missing assessments
are excluded. See `docs/recommendation-safety.md` for the assessment policy and run the read-only
readiness audit after importing data:

```bash
./scripts/uv run python backend/scripts/audit_recommendation_readiness.py
```

Identifiable recommendation interactions are stored only after separate, versioned
personalization consent. They expire after 365 days, and withdrawal deletes them without removing
the user's core favourites, history or planner data. Docker Compose runs the daily retention
worker; a purge can also be run manually:

```bash
./scripts/uv run python backend/scripts/purge_expired_recommendation_events.py
```

See `docs/recommendation-events.md` for the event contract and privacy boundaries.

Generate the isolated 12-persona, 500-user, 90-day synthetic training dataset from the actual
imported recipe catalog with:

```bash
./scripts/uv run python backend/scripts/generate_synthetic_recommendation_data.py
```

Evaluate the offline popularity and seasonal TF-IDF baselines with the dedicated ML dependency
group:

```bash
./scripts/uv run --group ml python backend/scripts/evaluate_recommendation_baselines.py
```

Tune, train and package the synthetic LightGBM LambdaRank prototype with:

```bash
./scripts/uv run --group ml python backend/scripts/train_recommendation_ranker.py
```

The generator creates a new checksummed run under `datasets/synthetic/runs/` and never overwrites
an existing run. See `docs/synthetic-personas.md` for the persona definitions, temporal split and
evaluation restrictions.

## Auth and User Endpoints

Register with JSON:

```bash
curl -X POST http://localhost:8001/api/v1/users \
  -H "Content-Type: application/json" \
  -H "CF-IPCountry: GB" \
  -d '{"email":"user@example.com","password":"correct-horse-battery"}'
```

Login uses OAuth2 password form data:

```bash
curl -X POST http://localhost:8001/api/v1/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user@example.com&password=correct-horse-battery"
```

The token response includes both `access_token` and `refresh_token`. Refresh tokens are
opaque, stored hashed in the database, expire after 30 days by default, and rotate on use:

```bash
curl -X POST http://localhost:8001/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"<refresh-token>"}'
```

Logout revokes the submitted refresh token for the current client session:

```bash
curl -X POST http://localhost:8001/api/v1/auth/logout \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"<refresh-token>"}'
```

Password reset requests use generic responses to avoid revealing whether an email is registered:

```bash
curl -X POST http://localhost:8001/api/v1/auth/password-reset/request \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com"}'
```

Confirm the reset with the token sent to the user:

```bash
curl -X POST http://localhost:8001/api/v1/auth/password-reset/confirm \
  -H "Content-Type: application/json" \
  -d '{"reset_token":"<reset-token>","new_password":"new-correct-horse-battery"}'
```

Configure `SMTP_HOST`, `SMTP_FROM_EMAIL`, and optional SMTP authentication settings to deliver
one-time reset tokens. Production configuration fails at startup if delivery is not configured.

Authenticated requests use the returned bearer token:

```bash
curl http://localhost:8001/api/v1/users/me \
  -H "Authorization: Bearer <token>"
```

Coarse profile location can be inferred from trusted proxy headers with:

```bash
curl -X POST http://localhost:8001/api/v1/users/me/location/coarse \
  -H "Authorization: Bearer <token>" \
  -H "CF-IPCountry: GB" \
  -H "CF-Region-Code: LND"
```

Set `TRUST_PROXY_LOCATION_HEADERS=true` only when the API is reachable exclusively through a proxy
that overwrites these headers. They are ignored by default.
