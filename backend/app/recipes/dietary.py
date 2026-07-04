import re
from collections.abc import Iterable

from app.data.enums import DietaryRule, DietPattern

MEAT_TERMS = {
    "bacon",
    "beef",
    "chicken",
    "duck",
    "goat",
    "ham",
    "lamb",
    "meat",
    "mince",
    "mutton",
    "pancetta",
    "pork",
    "prosciutto",
    "sausage",
    "sausages",
    "turkey",
    "veal",
}
FISH_SEAFOOD_TERMS = {
    "anchovy",
    "calamari",
    "clam",
    "clams",
    "cod",
    "crab",
    "fish",
    "haddock",
    "lobster",
    "mussels",
    "octopus",
    "oyster",
    "oysters",
    "prawn",
    "prawns",
    "salmon",
    "sardine",
    "sardines",
    "scallop",
    "scallops",
    "seafood",
    "shrimp",
    "shrimps",
    "squid",
    "tuna",
}
ANIMAL_PRODUCT_TERMS = {
    "butter",
    "cheese",
    "cream",
    "egg",
    "eggs",
    "ghee",
    "honey",
    "mayonnaise",
    "milk",
    "mozzarella",
    "parmesan",
    "yogurt",
    "yoghurt",
}
PORK_TERMS = {"bacon", "ham", "pancetta", "pork", "prosciutto", "sausage", "sausages"}
BEEF_TERMS = {"beef", "veal"}
SHELLFISH_TERMS = {
    "calamari",
    "clam",
    "clams",
    "crab",
    "lobster",
    "mussels",
    "octopus",
    "oyster",
    "oysters",
    "prawn",
    "prawns",
    "scallop",
    "scallops",
    "shrimp",
    "shrimps",
    "squid",
}
ALCOHOL_TERMS = {"beer", "brandy", "cider", "rum", "tequila", "vodka", "whiskey", "wine"}


def diet_excluded_terms(diet_pattern: DietPattern | None) -> set[str]:
    match diet_pattern:
        case DietPattern.PESCATARIAN:
            return set(MEAT_TERMS)
        case DietPattern.VEGETARIAN:
            return {*MEAT_TERMS, *FISH_SEAFOOD_TERMS}
        case DietPattern.VEGAN:
            return {*MEAT_TERMS, *FISH_SEAFOOD_TERMS, *ANIMAL_PRODUCT_TERMS}
        case _:
            return set()


def dietary_rule_excluded_terms(rules: Iterable[DietaryRule]) -> set[str]:
    terms: set[str] = set()
    for rule in rules:
        match rule:
            case DietaryRule.AVOID_PORK:
                terms.update(PORK_TERMS)
            case DietaryRule.AVOID_BEEF:
                terms.update(BEEF_TERMS)
            case DietaryRule.AVOID_SHELLFISH:
                terms.update(SHELLFISH_TERMS)
            case DietaryRule.AVOID_ALCOHOL:
                terms.update(ALCOHOL_TERMS)
    return terms


def dietary_patterns(terms: Iterable[str]) -> list[str]:
    return [_word_pattern(term) for term in sorted(set(terms), key=len, reverse=True)]


def _word_pattern(term: str) -> str:
    escaped = re.escape(term).replace(r"\ ", r"\s+")
    return rf"(^|[^[:alnum:]]){escaped}([^[:alnum:]]|$)"
