from typing import cast

from sqlalchemy import Table

from app.models import Produce, ProduceSeason


def test_produce_tables_are_configured() -> None:
    produce_table = cast(Table, Produce.__table__)
    seasons_table = cast(Table, ProduceSeason.__table__)

    assert Produce.__tablename__ == "produce"
    assert ProduceSeason.__tablename__ == "produce_seasons"
    assert cast(object, produce_table.c.name.unique) is not True
    assert {constraint.name for constraint in produce_table.constraints} >= {
        "ck_produce_type",
        "uq_produce_name_type",
    }
    assert next(iter(seasons_table.c.produce_id.foreign_keys)).ondelete == "CASCADE"
    assert {constraint.name for constraint in seasons_table.constraints} >= {
        "ck_produce_seasons_month",
        "uq_produce_seasons_produce_country_month_source",
    }
