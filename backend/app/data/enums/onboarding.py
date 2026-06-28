from enum import StrEnum


class OnboardingStatus(StrEnum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class OnboardingStep(StrEnum):
    PRIVACY = "privacy"
    LOCATION = "location"
    DIET = "diet"
    ALLERGIES = "allergies"
    DIETARY_RULES = "dietary_rules"
    CUISINES = "cuisines"
    PROTEINS = "proteins"
    REVIEW = "review"
    COMPLETE = "complete"
