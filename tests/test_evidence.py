from __future__ import annotations

import pytest

from rca.evidence import (
    export_evidence_dataset,
    fetch_all_evidence_records,
    get_store_day_evidence,
    list_dates,
    list_store_aliases,
)


def test_lists_cover_expected_scope() -> None:
    stores = list_store_aliases()
    dates = list_dates()
    assert len(stores) == 15
    assert stores[0] == "h018"
    assert len(dates) == 90
    assert dates[0] == "2024-03-28"
    assert dates[-1] == "2024-06-25"


def test_get_store_day_evidence_returns_joined_record() -> None:
    record = get_store_day_evidence("h263", "2024-06-24")
    assert record["store_alias"] == "h263"
    assert record["dt"] == "2024-06-24"
    assert record["sales"]["total_sales"] == pytest.approx(198.28)
    assert record["stockout"]["stockout_product_rate"] == pytest.approx(0.372671, rel=1e-4)
    assert record["discount"]["avg_discount"] == pytest.approx(0.906385, rel=1e-4)
    assert record["holiday"]["holiday_name_inferred"] == "normal_weekday"
    assert len(record["sales"]["hourly_sales"]) == 24
    assert len(record["stockout"]["hourly_stockout_rate"]) == 24


def test_get_store_day_evidence_rejects_unknown_store() -> None:
    with pytest.raises(ValueError, match="Unknown store_alias"):
        get_store_day_evidence("x999", "2024-06-24")


def test_get_store_day_evidence_rejects_unknown_date() -> None:
    with pytest.raises(ValueError, match="Unknown date"):
        get_store_day_evidence("h263", "2024-06-30")


def test_export_dataset_creates_expected_shape(tmp_path) -> None:
    records = fetch_all_evidence_records()
    assert len(records) == 1350

    output_path = tmp_path / "evidence_data.json"
    export_evidence_dataset(output_path)
    assert output_path.exists()
    text = output_path.read_text(encoding="utf-8")
    assert '"stores"' in text
    assert '"dates"' in text
    assert '"records"' in text
