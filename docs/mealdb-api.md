# TheMealDB API Exploration

Explored against the configured paid V2 API on 10 June 2026. API keys are deliberately omitted.

- Official API documentation: <https://www.themealdb.com/api.php>
- Terms of use: <https://www.themealdb.com/terms_of_use.php>
- Configured URL shape: `{RECIPES_BASE_URL}/{RECIPES_API_KEY}/{endpoint}`

The variables are present in the local environment, but `backend/app/core/config.py` does not yet
declare `recipes_base_url` or `recipes_api_key`. Pydantic currently ignores those extra variables,
so the eventual MealDB client must add them to `Settings` before using the shared config object.

The terms allow API content to be copied and modified when official endpoints are used. Paid API
users must mention TheMealDB as the data source, stay within the rate limit, and respect third-party
content rights. TheMealDB artwork must not be presented as Seasonly's own artwork.

## Endpoint Summary

All tested endpoints returned HTTP 200 for valid requests. Lookup, search, and filter requests with
no matches also returned HTTP 200, with `{"meals": null}` rather than an empty array.

| Endpoint | Result | Persistence use |
| --- | --- | --- |
| `search.php?s={name}` | Full meal objects | Search or targeted import |
| `search.php?f={character}` | Full meal objects | Best available full-catalog import |
| `lookup.php?i={id}` | One full meal object | Refresh a known recipe |
| `random.php` | One full meal object | Discovery only |
| `randomselection.php` | 10 full meal objects; paid API | Discovery only |
| `latest.php` | 10 full meal objects; paid API | Incremental refresh candidate |
| `popular.php` | 20 full meal objects; paid API, not documented on the API page | Discovery only |
| `categories.php` | Categories with ID, thumbnail, and description | Category metadata import |
| `list.php?c=list` | Category names only | Taxonomy/filter UI |
| `list.php?a=list` | Area and country names | Taxonomy/filter UI |
| `list.php?i=list` | Ingredients with ID and metadata | Ingredient metadata import |
| `filter.php?i={ingredients}` | Partial meal objects; comma-separated multi-filter is paid | Find candidate IDs |
| `filter.php?c={category}` | Partial meal objects | Find candidate IDs |
| `filter.php?a={area}` | Partial meal objects | Find candidate IDs |

The partial objects returned by filter endpoints contain `idMeal`, `strMeal`, and `strMealThumb`.
Area and category filters may additionally return `strArea` and `strCountry`. They must not replace
a previously persisted full meal. Resolve candidate IDs through `lookup.php?i={id}` before import.

## Response Shapes

Every full meal currently has the same top-level field names:

```text
idMeal, strMeal, strMealAlternate, strCategory, strArea, strCountry,
strInstructions, strMealThumb, strTags, strYoutube,
strIngredient1 ... strIngredient20, strMeasure1 ... strMeasure20,
strSource, strImageSource, strCreativeCommonsConfirmed, dateModified
```

Important data-quality behavior:

- IDs are numeric-looking strings and should be stored as text provider IDs.
- Ingredients and measures are paired numbered slots, not arrays.
- Unused slots can be `null`, `""`, or whitespace-only strings.
- Measures are unstructured display text such as `1/4 cup`, `3 cloves`, or `sprinkling`.
- `strTags` is a nullable comma-separated string.
- `dateModified` is nullable and uses a timestamp such as `2026-05-29 20:04:18`, without timezone.
- URLs and optional metadata can be null.
- Ingredient names in recipes usually, but not always, exactly match ingredient catalog names.

Observed catalog snapshot:

| Property | Observed value |
| --- | ---: |
| Recipes found by first-character search | 667 |
| Recipe categories | 14 |
| Areas used by recipes | 37 |
| Countries used by recipes | 51 |
| Ingredient catalog entries | 927 |
| Distinct ingredient names used by recipes | 880 |
| Exact case-insensitive ingredient catalog matches | 875 |
| Ingredient slots per recipe | 2 to 20, average 10.42 |
| Recipes with tags | 198 |
| Recipes with YouTube URL | 588 |
| Recipes with source URL | 631 |
| Recipes with `dateModified` | 363 |

The area list endpoint returned 195 area/country pairs, far more than are currently used by recipes.
Examples of recipe ingredient names that do not exactly match the ingredient catalog are `carrot`,
`clove`, `gruyere`, `gruyere cheese`, and `tomato purée`.

## Recommended PostgreSQL Model

Use normalized relational tables for fields Seasonly searches, joins, or recommends on. Also retain
the last full provider response as JSONB for provenance and forward compatibility.

This model is implemented in `backend/app/models/recipe.py` and migration
`0005_create_recipe_tables.py`. MealDB payload cleanup and full-record validation live in
`backend/app/recipes/normalization.py`.

### Data Catalog Organization

Use one source-level `DataKey`, `themealdb_recipes`, for the complete provider import. Its
`DataTarget`s are the persisted `recipe_categories`, `recipes`, `ingredients`,
`recipe_ingredients`, `tags`, and `recipe_tags` tables.

Do not create a `DataKey` for every table: join tables are outputs of the same provider import, not
independent datasets. Do not register a raw-file target because the source is an API and the last
raw provider objects are retained in JSONB columns. Register future versioned recipe feature sets
under a separate derived-data key when an ML feature pipeline actually exists.

### `recipes`

| Column | Suggested type | Notes |
| --- | --- | --- |
| `id` | UUID PK | Seasonly-owned identifier |
| `provider` | varchar | Initially `themealdb` |
| `provider_recipe_id` | varchar | Unique with `provider`; stores `idMeal` |
| `name` | varchar(200) | `strMeal` |
| `alternate_name` | varchar(200), nullable | `strMealAlternate` |
| `category_id` | UUID FK, nullable | Resolved from `strCategory` |
| `area` | varchar(120), nullable | `strArea` |
| `country_of_origin` | varchar(120), nullable | `strCountry`; explicit recipe origin, not ISO naming |
| `instructions` | text | `strInstructions` |
| `thumbnail_url` | text, nullable | `strMealThumb` |
| `source_url` | text, nullable | `strSource` |
| `youtube_url` | text, nullable | `strYoutube` |
| `image_source_url` | text, nullable | `strImageSource` |
| `creative_commons_confirmed` | varchar, nullable | Preserve provider value until semantics are confirmed |
| `provider_modified_at` | timestamp, nullable | Parse `dateModified` as provider-local/unknown timezone |
| `raw_payload` | jsonb | Last full provider object |
| `fetched_at` | timestamptz | When Seasonly fetched the full object |

Add a unique constraint on `(provider, provider_recipe_id)` and indexes on `name`, `category_id`,
`area`, and `country_of_origin`. PostgreSQL full-text or trigram indexes can be added when recipe
search is implemented.

### `recipe_categories`

Persist `idCategory`, name, description, thumbnail URL, provider, raw payload, and fetched time.
Meals reference categories by name, so import categories first and resolve the relationship during
meal normalization. Keep the raw category name on failed resolution or log it as an import error.

### `ingredients`

Persist provider ingredient ID, name, description, thumbnail URL, type, raw payload, and fetched
time. Use a case-insensitive unique key scoped to the provider for matching, but preserve original
casing for display.

### `recipe_ingredients`

| Column | Suggested type | Notes |
| --- | --- | --- |
| `recipe_id` | UUID FK | Part of unique key |
| `position` | smallint | 1 through 20; preserves provider order |
| `ingredient_id` | UUID FK, nullable | Nullable because catalog matching is imperfect |
| `ingredient_name_raw` | varchar(200) | Preserves recipe wording |
| `measure_raw` | varchar(200), nullable | Preserve display text; do not parse during import |

Use a unique constraint on `(recipe_id, position)` and an index on `ingredient_id`. This table is
the key link between seasonal produce and recipes. `produce.mealdb_name` can initially match
case-insensitively against `ingredients.name`; a dedicated produce-to-ingredient mapping table can
be added when aliases become more complex.

### `recipe_tags`

Normalize non-empty comma-separated tags into `tags` and `recipe_tags` only if tag filtering or
recommendation features will use them. Otherwise, a `tags text[]` column is sufficient for the
first version. Do not keep only the original comma-separated string.

## Ingestion Rules

1. Import category and ingredient metadata.
2. Discover recipes with `search.php?f={character}`. Include letters and digits because at least one
   current recipe starts with a digit.
3. Normalize all null, empty, and whitespace-only optional values to SQL `NULL`.
4. Convert the 20 ingredient/measure pairs into ordered `recipe_ingredients` rows.
5. Upsert recipes by `(provider, provider_recipe_id)` only from full meal responses.
6. Store the full response in `raw_payload` and record `fetched_at`.
7. Use `latest.php` for frequent checks, but periodically repeat the full first-character import:
   `dateModified` is absent on many records and the API offers no documented complete change feed.
8. Treat provider deletions conservatively. Mark unseen recipes inactive after repeated complete
   scans rather than immediately deleting them.

Do not persist random, latest, or popular membership as recipe attributes. Those endpoint results
are transient discovery/ranking views unless Seasonly explicitly needs historical snapshots.

## ML Readiness

The normalized model is a good foundation for content-based recommendations:

- `recipe_ingredients`, categories, tags, area, and country of origin can become sparse or
  embedding features.
- Ordered ingredient rows preserve source fidelity while linked ingredient IDs provide stable
  feature identities.
- Seasonal produce can join to ingredients through `produce.mealdb_name` initially.
- Raw payloads and provider timestamps make import behavior auditable.

It is intentionally not the complete ML architecture. Before training personalized models, add
timestamped recommendation events such as impressions, opens, saves, dismissals, and cooked
feedback. Training jobs should publish versioned feature snapshots or datasets; the recipe tables
hold current state and do not preserve every historical recipe revision. Avoid adding model scores
or embeddings directly to `recipes`; store them with a model/version identifier in dedicated
feature or prediction tables.

## Open Decisions

- Confirm with TheMealDB what timezone `dateModified` represents.
- Confirm the paid plan's actual rate limit; the public API and terms pages do not state a number.
- Decide whether Seasonly needs area/country taxonomy rows that have no recipes.
- Decide whether tags need normalized tables before implementing recommendations.
- Decide whether remote image URLs are sufficient or whether image caching is permitted and needed.
