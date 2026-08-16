from sqlalchemy import select
from sqlalchemy.dialects import postgresql

from app.data.enums import (
    Allergen,
    AllergenAssessmentMethod,
    AllergenAssessmentStatus,
)
from app.models import Recipe
from app.recipes.allergens import assess_ingredient_names
from app.recipes.service import recipe_is_verified_safe


def test_rules_only_confirm_detected_allergens() -> None:
    assessments = assess_ingredient_names(["Peanut butter", "Whole Milk", "Nutmeg", "Eggplant"])

    assert assessments[Allergen.PEANUTS] == (
        AllergenAssessmentStatus.CONTAINS,
        AllergenAssessmentMethod.RULES,
    )
    assert assessments[Allergen.MILK] == (
        AllergenAssessmentStatus.CONTAINS,
        AllergenAssessmentMethod.RULES,
    )
    assert assessments[Allergen.TREE_NUTS] == (
        AllergenAssessmentStatus.UNKNOWN,
        AllergenAssessmentMethod.UNASSESSED,
    )
    assert assessments[Allergen.EGGS] == (
        AllergenAssessmentStatus.UNKNOWN,
        AllergenAssessmentMethod.UNASSESSED,
    )


def test_safety_filter_requires_verified_absence_for_every_allergen() -> None:
    statement = select(Recipe.id).where(recipe_is_verified_safe({Allergen.PEANUTS, Allergen.MILK}))

    sql = str(
        statement.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )

    assert sql.count("EXISTS") == 2
    assert sql.count("does_not_contain") == 2
    assert "unknown" not in sql
