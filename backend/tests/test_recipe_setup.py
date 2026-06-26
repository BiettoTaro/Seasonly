from typing import cast

from sqlalchemy import Table

from app.models import Ingredient, Recipe, RecipeCategory, RecipeIngredient, RecipeTag, Tag


def test_recipe_tables_are_configured() -> None:
    category_table = cast(Table, RecipeCategory.__table__)
    ingredient_table = cast(Table, Ingredient.__table__)
    recipe_table = cast(Table, Recipe.__table__)
    recipe_ingredient_table = cast(Table, RecipeIngredient.__table__)
    tag_table = cast(Table, Tag.__table__)
    recipe_tag_table = cast(Table, RecipeTag.__table__)

    assert {constraint.name for constraint in category_table.constraints} >= {
        "uq_recipe_categories_provider_id",
        "uq_recipe_categories_provider_name",
    }
    assert {constraint.name for constraint in ingredient_table.constraints} >= {
        "uq_ingredients_provider_id",
        "uq_ingredients_provider_name",
    }
    assert {constraint.name for constraint in recipe_table.constraints} >= {
        "uq_recipes_provider_id"
    }
    assert {"category_id", "category_name_raw", "area", "country_of_origin"} <= set(
        recipe_table.c.keys()
    )
    assert recipe_table.c.category_name_raw.nullable is True
    assert recipe_table.c.area.nullable is True
    assert recipe_table.c.country_of_origin.nullable is True
    assert recipe_table.c.category_id.index is True
    assert recipe_table.c.area.index is True
    assert recipe_table.c.country_of_origin.index is True
    assert next(iter(recipe_table.c.category_id.foreign_keys)).ondelete == "SET NULL"
    assert recipe_ingredient_table.c.recipe_id.primary_key is True
    assert recipe_ingredient_table.c.position.primary_key is True
    assert next(iter(recipe_ingredient_table.c.recipe_id.foreign_keys)).ondelete == "CASCADE"
    assert next(iter(recipe_ingredient_table.c.ingredient_id.foreign_keys)).ondelete == "SET NULL"
    assert {constraint.name for constraint in recipe_ingredient_table.constraints} >= {
        "ck_recipe_ingredients_position"
    }
    assert cast(object, tag_table.c.normalized_name.unique) is True
    assert recipe_tag_table.c.recipe_id.primary_key is True
    assert recipe_tag_table.c.tag_id.primary_key is True
