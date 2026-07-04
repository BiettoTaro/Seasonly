import uuid
from datetime import UTC, datetime
from typing import TypedDict

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.data_key import DataKey
from app.models import (
    DataImportRun,
    Ingredient,
    Recipe,
    RecipeCategory,
    RecipeIngredient,
    RecipeTag,
    Tag,
)
from app.recipes.normalization import (
    MEALDB_PROVIDER,
    NormalizedCategory,
    NormalizedIngredient,
    NormalizedRecipe,
    normalize_mealdb_category,
    normalize_mealdb_ingredient,
    normalize_mealdb_recipe,
    normalize_name,
)


class RecipeImportSnapshot(TypedDict):
    categories: list[NormalizedCategory]
    ingredients: list[NormalizedIngredient]
    recipes: list[NormalizedRecipe]


INSERT_BATCH_SIZE = 1_000


def utc_now() -> datetime:
    return datetime.now(UTC)


def normalize_snapshot(
    *,
    categories: list[dict[str, object]],
    ingredients: list[dict[str, object]],
    recipes: list[dict[str, object]],
) -> RecipeImportSnapshot:
    snapshot = RecipeImportSnapshot(
        categories=[normalize_mealdb_category(payload) for payload in categories],
        ingredients=[normalize_mealdb_ingredient(payload) for payload in ingredients],
        recipes=[normalize_mealdb_recipe(payload) for payload in recipes],
    )
    if not snapshot["categories"]:
        raise ValueError("MealDB category snapshot is empty")
    if not snapshot["ingredients"]:
        raise ValueError("MealDB ingredient snapshot is empty")
    if not snapshot["recipes"]:
        raise ValueError("MealDB recipe snapshot is empty")
    return snapshot


async def create_import_run(session: AsyncSession) -> DataImportRun:
    run = DataImportRun(
        data_key=DataKey.THEMEALDB_RECIPES.value,
        status="running",
    )
    session.add(run)
    await session.commit()
    return run


async def complete_import_run(
    session: AsyncSession,
    run_id: uuid.UUID,
    snapshot: RecipeImportSnapshot,
) -> None:
    _ = await session.execute(
        update(DataImportRun)
        .where(DataImportRun.id == run_id)
        .values(
            status="succeeded",
            completed_at=utc_now(),
            record_counts={
                "recipe_categories": len(snapshot["categories"]),
                "ingredients": len(snapshot["ingredients"]),
                "recipes": len(snapshot["recipes"]),
            },
            error_message=None,
        )
    )
    await session.commit()


async def fail_import_run(session: AsyncSession, run_id: uuid.UUID, error: Exception) -> None:
    _ = await session.execute(
        update(DataImportRun)
        .where(DataImportRun.id == run_id)
        .values(
            status="failed",
            completed_at=utc_now(),
            error_message=str(error)[:4_000],
        )
    )
    await session.commit()


async def import_snapshot(
    session: AsyncSession,
    snapshot: RecipeImportSnapshot,
    *,
    fetched_at: datetime | None = None,
) -> None:
    imported_at = fetched_at if fetched_at is not None else utc_now()

    await _upsert_categories(session, snapshot["categories"], imported_at)
    category_ids = await _category_ids_by_normalized_name(session)

    await _upsert_ingredients(session, snapshot["ingredients"], imported_at)
    ingredient_ids = await _ingredient_ids_by_normalized_name(session)

    await _upsert_recipes(session, snapshot["recipes"], category_ids, imported_at)
    recipe_ids = await _recipe_ids_by_provider_id(session)
    imported_recipe_ids = {
        recipe_ids[recipe["provider_recipe_id"]] for recipe in snapshot["recipes"]
    }

    _ = await session.execute(
        delete(RecipeIngredient).where(RecipeIngredient.recipe_id.in_(imported_recipe_ids))
    )
    _ = await session.execute(delete(RecipeTag).where(RecipeTag.recipe_id.in_(imported_recipe_ids)))
    await _insert_recipe_ingredients(session, snapshot["recipes"], recipe_ids, ingredient_ids)
    await _upsert_and_link_tags(session, snapshot["recipes"], recipe_ids)


async def _upsert_categories(
    session: AsyncSession,
    categories: list[NormalizedCategory],
    fetched_at: datetime,
) -> None:
    values = [{"id": uuid.uuid4(), **category, "fetched_at": fetched_at} for category in categories]
    statement = insert(RecipeCategory).values(values)
    statement = statement.on_conflict_do_update(
        constraint="uq_recipe_categories_provider_id",
        set_={
            "name": statement.excluded.name,
            "description": statement.excluded.description,
            "thumbnail_url": statement.excluded.thumbnail_url,
            "raw_payload": statement.excluded.raw_payload,
            "fetched_at": statement.excluded.fetched_at,
        },
    )
    _ = await session.execute(statement)


async def _upsert_ingredients(
    session: AsyncSession,
    ingredients: list[NormalizedIngredient],
    fetched_at: datetime,
) -> None:
    values = [
        {"id": uuid.uuid4(), **ingredient, "fetched_at": fetched_at} for ingredient in ingredients
    ]
    statement = insert(Ingredient).values(values)
    statement = statement.on_conflict_do_update(
        constraint="uq_ingredients_provider_id",
        set_={
            "name": statement.excluded.name,
            "normalized_name": statement.excluded.normalized_name,
            "description": statement.excluded.description,
            "thumbnail_url": statement.excluded.thumbnail_url,
            "type": statement.excluded.type,
            "raw_payload": statement.excluded.raw_payload,
            "fetched_at": statement.excluded.fetched_at,
        },
    )
    _ = await session.execute(statement)


async def _upsert_recipes(
    session: AsyncSession,
    recipes: list[NormalizedRecipe],
    category_ids: dict[str, uuid.UUID],
    fetched_at: datetime,
) -> None:
    values: list[dict[str, object]] = []
    for recipe in recipes:
        category_name = recipe["category_name_raw"]
        values.append(
            {
                "id": uuid.uuid4(),
                "provider": recipe["provider"],
                "provider_recipe_id": recipe["provider_recipe_id"],
                "name": recipe["name"],
                "alternate_name": recipe["alternate_name"],
                "category_id": (
                    category_ids.get(normalize_name(category_name))
                    if category_name is not None
                    else None
                ),
                "category_name_raw": category_name,
                "area": recipe["area"],
                "country_of_origin": recipe["country_of_origin"],
                "instructions": recipe["instructions"],
                "thumbnail_url": recipe["thumbnail_url"],
                "source_url": recipe["source_url"],
                "youtube_url": recipe["youtube_url"],
                "image_source_url": recipe["image_source_url"],
                "creative_commons_confirmed": recipe["creative_commons_confirmed"],
                "provider_modified_at": recipe["provider_modified_at"],
                "raw_payload": recipe["raw_payload"],
                "is_active": True,
                "first_seen_at": fetched_at,
                "last_seen_at": fetched_at,
                "fetched_at": fetched_at,
            }
        )

    statement = insert(Recipe).values(values)
    statement = statement.on_conflict_do_update(
        constraint="uq_recipes_provider_id",
        set_={
            "name": statement.excluded.name,
            "alternate_name": statement.excluded.alternate_name,
            "category_id": statement.excluded.category_id,
            "category_name_raw": statement.excluded.category_name_raw,
            "area": statement.excluded.area,
            "country_of_origin": statement.excluded.country_of_origin,
            "instructions": statement.excluded.instructions,
            "thumbnail_url": statement.excluded.thumbnail_url,
            "source_url": statement.excluded.source_url,
            "youtube_url": statement.excluded.youtube_url,
            "image_source_url": statement.excluded.image_source_url,
            "creative_commons_confirmed": statement.excluded.creative_commons_confirmed,
            "provider_modified_at": statement.excluded.provider_modified_at,
            "raw_payload": statement.excluded.raw_payload,
            "is_active": True,
            "last_seen_at": statement.excluded.last_seen_at,
            "fetched_at": statement.excluded.fetched_at,
        },
    )
    _ = await session.execute(statement)


async def _insert_recipe_ingredients(
    session: AsyncSession,
    recipes: list[NormalizedRecipe],
    recipe_ids: dict[str, uuid.UUID],
    ingredient_ids: dict[str, uuid.UUID],
) -> None:
    values = [
        {
            "recipe_id": recipe_ids[recipe["provider_recipe_id"]],
            "position": ingredient["position"],
            "ingredient_id": ingredient_ids.get(ingredient["ingredient_name_normalized"]),
            "ingredient_name_raw": ingredient["ingredient_name_raw"],
            "measure_raw": ingredient["measure_raw"],
        }
        for recipe in recipes
        for ingredient in recipe["ingredients"]
    ]
    if values:
        for batch in batches(values):
            _ = await session.execute(insert(RecipeIngredient).values(batch))


async def _upsert_and_link_tags(
    session: AsyncSession,
    recipes: list[NormalizedRecipe],
    recipe_ids: dict[str, uuid.UUID],
) -> None:
    tags_by_normalized_name = {
        normalize_name(tag): tag for recipe in recipes for tag in recipe["tags"]
    }
    if not tags_by_normalized_name:
        return

    values = [
        {"id": uuid.uuid4(), "name": name, "normalized_name": normalized_name}
        for normalized_name, name in tags_by_normalized_name.items()
    ]
    statement = insert(Tag).values(values)
    statement = statement.on_conflict_do_update(
        index_elements=[Tag.normalized_name],
        set_={"name": statement.excluded.name},
    )
    _ = await session.execute(statement)
    tag_ids = {
        normalized_name: tag_id
        for tag_id, normalized_name in (
            row.tuple()
            for row in (
                await session.execute(
                    select(Tag.id, Tag.normalized_name).where(
                        Tag.normalized_name.in_(tags_by_normalized_name)
                    )
                )
            ).all()
        )
    }
    links = [
        {
            "recipe_id": recipe_ids[recipe["provider_recipe_id"]],
            "tag_id": tag_ids[normalize_name(tag)],
        }
        for recipe in recipes
        for tag in recipe["tags"]
    ]
    if links:
        for batch in batches(links):
            _ = await session.execute(insert(RecipeTag).values(batch))


def batches[T](values: list[T], batch_size: int = INSERT_BATCH_SIZE) -> list[list[T]]:
    return [values[index : index + batch_size] for index in range(0, len(values), batch_size)]


async def _category_ids_by_normalized_name(session: AsyncSession) -> dict[str, uuid.UUID]:
    result = await session.execute(
        select(RecipeCategory.id, RecipeCategory.name).where(
            RecipeCategory.provider == MEALDB_PROVIDER
        )
    )
    return {
        normalize_name(name): category_id
        for category_id, name in (row.tuple() for row in result.all())
    }


async def _ingredient_ids_by_normalized_name(session: AsyncSession) -> dict[str, uuid.UUID]:
    result = await session.execute(
        select(Ingredient.id, Ingredient.normalized_name).where(
            Ingredient.provider == MEALDB_PROVIDER
        )
    )
    return {
        normalized_name: ingredient_id
        for ingredient_id, normalized_name in (row.tuple() for row in result.all())
    }


async def _recipe_ids_by_provider_id(session: AsyncSession) -> dict[str, uuid.UUID]:
    result = await session.execute(
        select(Recipe.id, Recipe.provider_recipe_id).where(Recipe.provider == MEALDB_PROVIDER)
    )
    return {
        provider_recipe_id: recipe_id
        for recipe_id, provider_recipe_id in (row.tuple() for row in result.all())
    }
