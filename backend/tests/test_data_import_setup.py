from typing import cast

from sqlalchemy import Table

from app.models import DataImportRun


def test_data_import_run_table_is_configured() -> None:
    table = cast(Table, DataImportRun.__table__)

    assert DataImportRun.__tablename__ == "data_import_runs"
    assert table.c.data_key.index is True
    assert table.c.status.index is True
    assert "record_counts" in table.c
    assert "recipe_count" not in table.c
    assert {constraint.name for constraint in table.constraints} >= {"ck_data_import_runs_status"}
