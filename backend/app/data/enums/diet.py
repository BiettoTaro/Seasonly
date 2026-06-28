from enum import StrEnum


class DietPattern(StrEnum):
    OMNIVORE = "omnivore"
    FLEXITARIAN = "flexitarian"
    PESCATARIAN = "pescatarian"
    VEGETARIAN = "vegetarian"
    VEGAN = "vegan"


class DietaryRule(StrEnum):
    AVOID_PORK = "avoid_pork"
    AVOID_BEEF = "avoid_beef"
    AVOID_ALCOHOL = "avoid_alcohol"
    AVOID_SHELLFISH = "avoid_shellfish"


class ProteinPreference(StrEnum):
    CHICKEN = "chicken"
    TURKEY = "turkey"
    BEEF = "beef"
    PORK = "pork"
    LAMB = "lamb"
    FISH = "fish"
    SEAFOOD = "seafood"
    EGGS = "eggs"
    TOFU = "tofu"
    LEGUMES = "legumes"
