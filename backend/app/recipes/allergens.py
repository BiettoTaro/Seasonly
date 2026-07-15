import re
from collections.abc import Iterable

from app.data.enums import Allergen

ALLERGEN_TERMS: dict[Allergen, set[str]] = {
    Allergen.CELERY: {"celery", "celeriac"},
    Allergen.CEREALS_CONTAINING_GLUTEN: {
        "barley",
        "bread",
        "breadcrumbs",
        "bulgur",
        "flour",
        "noodles",
        "pasta",
        "rye",
        "spaghetti",
        "wheat",
    },
    Allergen.CRUSTACEANS: {
        "crab",
        "crayfish",
        "lobster",
        "prawn",
        "prawns",
        "shrimp",
        "shrimps",
    },
    Allergen.EGGS: {"egg", "eggs", "mayonnaise", "mayo"},
    Allergen.FISH: {
        "anchovy",
        "cod",
        "fish",
        "haddock",
        "salmon",
        "sardine",
        "sardines",
        "tuna",
    },
    Allergen.LUPIN: {"lupin"},
    Allergen.MILK: {
        "butter",
        "cheese",
        "cream",
        "creme fraiche",
        "ghee",
        "milk",
        "mozzarella",
        "parmesan",
        "yogurt",
        "yoghurt",
    },
    Allergen.MOLLUSCS: {
        "clam",
        "clams",
        "mussel",
        "mussels",
        "octopus",
        "oyster",
        "oysters",
        "scallop",
        "scallops",
        "squid",
    },
    Allergen.MUSTARD: {"mustard"},
    Allergen.PEANUTS: {"peanut", "peanuts"},
    Allergen.SESAME: {"sesame", "tahini"},
    Allergen.SOYBEANS: {"soy", "soya", "soybean", "soybeans", "tofu"},
    Allergen.SULPHUR_DIOXIDE_AND_SULPHITES: {
        "dried apricots",
        "dried fruit",
        "sulphite",
        "sulphites",
        "sulfite",
        "sulfites",
        "wine",
    },
    Allergen.TREE_NUTS: {
        "almond",
        "almonds",
        "cashew",
        "cashews",
        "hazelnut",
        "hazelnuts",
        "pecan",
        "pecans",
        "pistachio",
        "pistachios",
        "walnut",
        "walnuts",
    },
}


def allergen_terms(allergens: Iterable[Allergen]) -> set[str]:
    return {term for allergen in allergens for term in ALLERGEN_TERMS.get(allergen, set())}


def allergen_patterns(allergens: Iterable[Allergen]) -> list[str]:
    return [
        _word_pattern(term) for term in sorted(allergen_terms(allergens), key=len, reverse=True)
    ]


def _word_pattern(term: str) -> str:
    escaped = re.escape(term).replace(r"\ ", r"\s+")
    return rf"(^|[^[:alnum:]]){escaped}([^[:alnum:]]|$)"
