from app.data.contracts import DataTarget
from app.data.enums import DataTargetType

# Normalized tables
RECIPE_CATEGORIES_TARGET = DataTarget(
    target_type=DataTargetType.NORMALIZED_TABLE,
    name="recipe_categories",
    description="TheMealDB category metadata used for filtering recipes.",
)
RECIPES_TARGET = DataTarget(
    target_type=DataTargetType.NORMALIZED_TABLE,
    name="recipes",
    description="Validated recipes with origin, category, provenance, and lifecycle metadata.",
)
INGREDIENTS_TARGET = DataTarget(
    target_type=DataTargetType.NORMALIZED_TABLE,
    name="ingredients",
    description="TheMealDB ingredient catalog with stable provider identities.",
)
RECIPE_INGREDIENTS_TARGET = DataTarget(
    target_type=DataTargetType.NORMALIZED_TABLE,
    name="recipe_ingredients",
    description="Ordered recipe-to-ingredient relationships with raw measures.",
)
TAGS_TARGET = DataTarget(
    target_type=DataTargetType.NORMALIZED_TABLE,
    name="tags",
    description="Normalized recipe tag vocabulary.",
)
RECIPE_TAGS_TARGET = DataTarget(
    target_type=DataTargetType.NORMALIZED_TABLE,
    name="recipe_tags",
    description="Recipe-to-tag relationships used for filtering and derived features.",
)

THEMEALDB_RECIPE_TARGETS: tuple[DataTarget, ...] = (
    RECIPE_CATEGORIES_TARGET,
    RECIPES_TARGET,
    INGREDIENTS_TARGET,
    RECIPE_INGREDIENTS_TARGET,
    TAGS_TARGET,
    RECIPE_TAGS_TARGET,
)
