# Project Assistant Instructions

Use this folder for project-specific assistant notes, skills, and repeatable workflows.

## Current Guidance

- Keep the repository as a monolith unless the project requirements change.
- Prefer FastAPI, Pydantic, SQLAlchemy, PostgreSQL, uv, and Ruff for the backend.
- Keep iOS-specific project files under `ios/`.
- Document external datasets before importing them.
- Do not use git commands in any case, I will handle that manually.
- Do not make any changes to the project structure or files without my permission.
- Do not make any assumptions about any task. If you are not sure about something, ask me.

**Code quality:**
- DO NOT use fallbacks unless you really have to. Try to raise value errors etc when there is an issue. Always raise from the caught exception using "raise ... from e" when writing except blocks.
- Do not assume data structures - always verify by checking where DataKeys are created.
- Do not copy patterns from other nodes if they contradict this request or not requested at all - pause and ask if unsure.
- Keep code DRY - if repeating full methods across nodes, ask if we should use mixins or a base node (an abstract base node that also inherits from Node) instead.
- Check that DataKey types match actual data structures
- Enums: Use existing enums rather than strings when it is more preferred, and suggest new Enums when needed. Don't place Enums into node class files if it can be used by different nodes from different folders.
- Ask confirmations before writing anything

## Backend Data Layout Reminders

- Keep data-facing definitions inside `backend/app/data/`, not inside domain packages such as `backend/app/users/`.
- Data key enums live under `backend/app/data/data_key/`. If a domain needs its own key group, create a domain file there, for example `data_key/user.py`, and export it from `data_key/__init__.py`.
- Data target definitions live under `backend/app/data/data_target/`. Domain-specific targets should use files such as `data_target/user.py`, `data_target/produce.py`, or `data_target/recipes.py`.
- Data source registrations live under `backend/app/data/data_source/`. Domain-specific registrations should use files such as `data_source/produce.py`, `data_source/recipes.py`, or `data_source/recommendations.py`.
- The data registry lives in `backend/app/data/registry.py` and should only map `DataKey` values to imported `DataSourceRegistration` objects. Do not define inline `DataSourceRegistration(...)`, `DataSourceMetadata(...)`, or `DataTarget(...)` objects in the registry.
- Data-catalog contracts used by `DataSpec(type=...)` live under `backend/app/data/contracts/`, for example `contracts/user.py`; do not create another generic `schemas` package under `backend/app/data/`.
- API request/response schemas live under `backend/app/schemas/`, for example `backend/app/schemas/user.py` or `backend/app/schemas/auth.py`; do not place shared Pydantic API schemas inside domain packages such as `backend/app/users/`.
- ORM persistence models belong under `backend/app/models/`; do not mix SQLAlchemy models into the data catalog packages.
- Domain packages like `backend/app/users/` should contain user-domain services/helpers only when needed, not data catalog keys, targets, or shared schemas.

## Basedpyright Typing Reminders

- Run both project and file-specific checks when fixing editor diagnostics: `./scripts/uv run basedpyright` and, when needed, `./scripts/uv run basedpyright path/to/file.py`.
- File-specific basedpyright can behave differently from project mode. Fix the exact file the editor reports, not only the project-level command.
- Avoid leaking `Any` from dynamic APIs into assertions or constructors. For SQLAlchemy metadata in tests, cast `Model.__table__` to `sqlalchemy.Table` before reading table columns.
- SQLAlchemy column attributes such as `.unique` may still be typed as `Any`; cast that specific value to `object` before asserting, for example `assert cast(object, table.c.email.unique) is True`.
- Inside `pytest.raises`, assign intentionally unused call results to `_` when basedpyright reports `reportUnusedCallResult`.
- Avoid dynamic enum namespace access like `DataKey.User.PROFILE` at typed call sites if it causes `Any`; use the directly typed enum such as `UserDataKey.PROFILE` while keeping dynamic aliases only as runtime convenience.
