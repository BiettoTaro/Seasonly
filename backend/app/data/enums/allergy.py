from enum import StrEnum


class AllergyProfileStatus(StrEnum):
    NOT_PROVIDED = "not_provided"
    NO_KNOWN_ALLERGIES = "no_known_allergies"
    PROVIDED = "provided"


class Allergen(StrEnum):
    CELERY = "celery"
    CEREALS_CONTAINING_GLUTEN = "cereals_containing_gluten"
    CRUSTACEANS = "crustaceans"
    EGGS = "eggs"
    FISH = "fish"
    LUPIN = "lupin"
    MILK = "milk"
    MOLLUSCS = "molluscs"
    MUSTARD = "mustard"
    PEANUTS = "peanuts"
    SESAME = "sesame"
    SOYBEANS = "soybeans"
    SULPHUR_DIOXIDE_AND_SULPHITES = "sulphur_dioxide_and_sulphites"
    TREE_NUTS = "tree_nuts"
