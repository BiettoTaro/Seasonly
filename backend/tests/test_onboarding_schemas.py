import pytest
from pydantic import ValidationError

from app.data.enums import (
    Allergen,
    AllergyProfileStatus,
    CountryCode,
    CuisinePreferenceStatus,
    LocationSource,
    ProteinPreference,
)
from app.schemas.onboarding import (
    AllergyUpdate,
    CuisineUpdate,
    LocationUpdate,
    ProteinUpdate,
)


def test_location_update_normalizes_region_code() -> None:
    payload = LocationUpdate(
        country_code=CountryCode.UNITED_KINGDOM,
        region_code="gb-eng",
        source=LocationSource.DEVICE,
    )

    assert payload.country_code == "GB"
    assert payload.region_code == "GB-ENG"


def test_allergy_update_requires_consent_when_allergens_are_stored() -> None:
    with pytest.raises(ValidationError, match="Explicit consent is required"):
        _ = AllergyUpdate(
            status=AllergyProfileStatus.PROVIDED,
            allergens={Allergen.PEANUTS},
            explicit_consent=False,
        )


def test_allergy_update_allows_skipping_without_consent() -> None:
    payload = AllergyUpdate(status=AllergyProfileStatus.NOT_PROVIDED)

    assert payload.allergens == set()
    assert payload.explicit_consent is False


def test_cuisine_update_rejects_duplicate_areas() -> None:
    with pytest.raises(ValidationError, match="must not contain duplicates"):
        _ = CuisineUpdate(
            status=CuisinePreferenceStatus.PROVIDED,
            areas=["Italian", " italian "],
        )


def test_cuisine_update_allows_no_preference() -> None:
    payload = CuisineUpdate(status=CuisinePreferenceStatus.NO_PREFERENCE)

    assert payload.areas == []


def test_protein_update_rejects_duplicates() -> None:
    with pytest.raises(ValidationError, match="must not contain duplicates"):
        _ = ProteinUpdate(proteins=[ProteinPreference.CHICKEN, ProteinPreference.CHICKEN])
