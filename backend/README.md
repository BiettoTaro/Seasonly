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
curl "http://localhost:8000/api/v1/produce/seasonal?country=GB&month=6"
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
curl "http://localhost:8000/api/v1/recipes/seasonal?month=6&category=Vegetarian" \
  -H "Authorization: Bearer <token>"
```

The profile country applies only to seasonal produce matching. Recipe `origin` is an independent,
optional filter.

## Auth and User Endpoints

Register with JSON:

```bash
curl -X POST http://localhost:8000/api/v1/users \
  -H "Content-Type: application/json" \
  -H "CF-IPCountry: GB" \
  -d '{"email":"user@example.com","password":"correct-horse-battery"}'
```

Login uses OAuth2 password form data:

```bash
curl -X POST http://localhost:8000/api/v1/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user@example.com&password=correct-horse-battery"
```

The token response includes both `access_token` and `refresh_token`. Refresh tokens are
opaque, stored hashed in the database, expire after 30 days by default, and rotate on use:

```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"<refresh-token>"}'
```

Logout revokes the submitted refresh token for the current client session:

```bash
curl -X POST http://localhost:8000/api/v1/auth/logout \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"<refresh-token>"}'
```

Password reset requests use generic responses to avoid revealing whether an email is registered:

```bash
curl -X POST http://localhost:8000/api/v1/auth/password-reset/request \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com"}'
```

Confirm the reset with the token sent to the user:

```bash
curl -X POST http://localhost:8000/api/v1/auth/password-reset/confirm \
  -H "Content-Type: application/json" \
  -d '{"reset_token":"<reset-token>","new_password":"new-correct-horse-battery"}'
```

TODO: add an email provider adapter to deliver reset links.
TODO: add a local/dev-only reset-token sink for manual testing without exposing tokens in API responses.

Authenticated requests use the returned bearer token:

```bash
curl http://localhost:8000/api/v1/users/me \
  -H "Authorization: Bearer <token>"
```

Coarse profile location can be inferred from trusted proxy headers with:

```bash
curl -X POST http://localhost:8000/api/v1/users/me/location/coarse \
  -H "Authorization: Bearer <token>" \
  -H "CF-IPCountry: GB" \
  -H "CF-Region-Code: LND"
```
