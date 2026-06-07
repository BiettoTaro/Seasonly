from app.data.enums import CountryCode, Month, ProduceType


def test_seasonal_enums_use_storage_values() -> None:
    assert Month.JANUARY.value == 1
    assert Month.DECEMBER.value == 12
    assert ProduceType.FRUIT.value == "fruit"
    assert ProduceType.VEGETABLE.value == "vegetable"
    assert CountryCode.ESTONIA.value == "EE"
    assert CountryCode.UNITED_KINGDOM.value == "GB"
