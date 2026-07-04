from typing import cast

from sqlalchemy import Table

from app.models import UserPlannedMeal, UserRecipeFavourite, UserRecipeHistory


def test_user_recipe_tables_are_configured() -> None:
    favourites_table = cast(Table, UserRecipeFavourite.__table__)
    history_table = cast(Table, UserRecipeHistory.__table__)
    planner_table = cast(Table, UserPlannedMeal.__table__)

    assert favourites_table.c.user_id.primary_key is True
    assert favourites_table.c.recipe_id.primary_key is True
    assert next(iter(favourites_table.c.user_id.foreign_keys)).ondelete == "CASCADE"
    assert next(iter(favourites_table.c.recipe_id.foreign_keys)).ondelete == "CASCADE"

    assert history_table.c.user_id.primary_key is True
    assert history_table.c.recipe_id.primary_key is True
    assert next(iter(history_table.c.user_id.foreign_keys)).ondelete == "CASCADE"
    assert next(iter(history_table.c.recipe_id.foreign_keys)).ondelete == "CASCADE"

    assert planner_table.c.user_id.index is True
    assert planner_table.c.recipe_id.index is True
    assert {constraint.name for constraint in planner_table.constraints} >= {
        "ck_user_planned_meals_day",
        "ck_user_planned_meals_slot",
        "uq_user_planned_meals_entry",
    }
