from app.data.enums import DietaryRule, DietPattern
from app.recipes.dietary import diet_excluded_terms, dietary_rule_excluded_terms


def test_pescatarian_excludes_meat_but_allows_fish_terms() -> None:
    terms = diet_excluded_terms(DietPattern.PESCATARIAN)

    assert "lamb" in terms
    assert "beef" in terms
    assert "chicken" in terms
    assert "salmon" not in terms
    assert "prawn" not in terms


def test_dietary_rules_add_specific_exclusions() -> None:
    terms = dietary_rule_excluded_terms(
        {DietaryRule.AVOID_BEEF, DietaryRule.AVOID_SHELLFISH}
    )

    assert "beef" in terms
    assert "shrimp" in terms
    assert "chicken" not in terms
