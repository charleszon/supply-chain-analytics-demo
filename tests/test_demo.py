import importlib.util
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]


def modules():
    assert importlib.util.find_spec("demo"), "demo package must exist"
    assert importlib.util.find_spec("demo.pipeline"), "demo.pipeline must exist"
    from demo import analytics, pipeline

    return pipeline, analytics


def test_generation_is_repeatable_and_relational(tmp_path):
    pipeline, _ = modules()
    left = pipeline.generate(42)
    right = pipeline.generate(42)
    assert set(left) == {"suppliers", "orders", "costs", "milestones", "schedule"}
    for name, frame in left.items():
        pd.testing.assert_frame_equal(frame, right[name])
        assert not frame.empty
    for table_name, column in [("orders", "delivered_date"), ("milestones", "completed_date")]:
        recorded = left[table_name][column].dropna()
        assert recorded.le(pipeline.AS_OF).all()
    assert len(left["orders"]) == 360
    assert left["orders"]["order_id"].is_unique
    assert set(left["orders"]["supplier_id"]) <= set(left["suppliers"]["supplier_id"])
    assert left["orders"]["quantity"].gt(0).all()
    assert left["orders"]["delivered_quantity"].le(left["orders"]["quantity"]).all()
    assert len(left["milestones"]) == 4 * len(left["orders"])
    pipeline.build(tmp_path)
    tables = pipeline.load(tmp_path)
    assert len(tables["orders"]) == 360
    assert (tmp_path / "warehouse.duckdb").exists()
    pipeline.build(tmp_path)
    assert len(pipeline.load(tmp_path)["orders"]) == 360


def test_delivery_metrics_use_complete_deliveries_and_snapshot():
    _, analytics = modules()
    orders = pd.DataFrame(
        {
            "order_id": ["1", "2", "3", "4"],
            "quantity": [100, 100, 100, 100],
            "delivered_quantity": [100, 100, 50, 0],
            "due_date": pd.to_datetime(["2026-07-01", "2026-07-01", "2026-07-01", "2026-08-01"]),
            "delivered_date": pd.to_datetime(["2026-07-01", "2026-07-02", "2026-07-01", None]),
        }
    )
    result = analytics.delivery(orders)
    assert list(result["status"]) == ["On time", "Late", "Overdue", "Upcoming"]
    summary = analytics.summary(result)
    assert summary["delivery_rate"] == pytest.approx(0.625)
    assert summary["on_time_rate"] == pytest.approx(0.5)
    assert summary["overdue_orders"] == 1


def test_empty_filters_and_zero_capacity_are_handled():
    pipeline, analytics = modules()
    tables = pipeline.generate()
    empty = analytics.filter_orders(tables["orders"], ["Missing"], [], [])
    assert empty.empty
    assert analytics.summary(analytics.delivery(empty))["delivery_rate"] == 0
    capacity = analytics.capacity(tables["orders"], tables["suppliers"])
    assert capacity["utilization"].ge(0).all()
    suppliers = tables["suppliers"].copy()
    suppliers["monthly_capacity"] = 0
    with pytest.raises(ValueError, match="capacity"):
        analytics.capacity(tables["orders"], suppliers)


def test_pipeline_rejects_invalid_input():
    pipeline, _ = modules()
    tables = pipeline.generate()
    tables["orders"].loc[0, "quantity"] = -1
    with pytest.raises(ValueError, match="quantity"):
        pipeline.validate(tables)
    tables = pipeline.generate()
    tables["orders"] = tables["orders"].drop(columns="supplier_id")
    with pytest.raises(ValueError, match="supplier_id"):
        pipeline.validate(tables)
    tables = pipeline.generate()
    tables["orders"].loc[0, "supplier_id"] = "UNKNOWN"
    with pytest.raises(ValueError, match="supplier"):
        pipeline.validate(tables)


def test_every_dashboard_view_and_empty_filter(monkeypatch, tmp_path):
    from streamlit.testing.v1 import AppTest

    pipeline, _ = modules()
    pipeline.build(tmp_path)
    monkeypatch.setenv("DEMO_DATA_DIR", str(tmp_path))
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    assert not app.exception
    assert len(app.radio[0].options) == 8
    for page in app.radio[0].options:
        app.radio[0].set_value(page).run()
        assert not app.exception, page
        assert app.get("download_button")[0].label == "Download filtered orders · CSV"
    app.multiselect[0].set_value(["Brand A"]).run()
    app.multiselect[1].set_value(["Supplier 01"]).run()
    app.multiselect[2].set_value(["Tops"]).run()
    for page in app.radio[0].options:
        app.radio[0].set_value(page).run()
        assert not app.exception, page
    app.multiselect[0].set_value([]).run()
    assert not app.exception
    assert len(app.info) >= 1


def test_dashboard_bootstraps_without_an_existing_database(monkeypatch, tmp_path):
    from streamlit.testing.v1 import AppTest

    monkeypatch.setenv("DEMO_DATA_DIR", str(tmp_path))
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    assert not app.exception
    assert (tmp_path / "warehouse.duckdb").exists()


def test_scan_detects_credentials_and_excluded_identifiers():
    from scripts.scan_publication import check_bytes

    token = ("ghp_" + "A" * 40).encode()
    assert any(hit["rule"] == "github_token" for hit in check_bytes("test.txt", token))
    assert any(
        hit["rule"] == "excluded_source_identifier"
        for hit in check_bytes("test.txt", b"Forbidden Demo Org", ["Forbidden Demo Org"])
    )
    assert not check_bytes("test.txt", b"Supplier 01; Brand A; DEMO-PO-0001")


def test_fixture_serialization_uses_canonical_lf(tmp_path):
    pipeline, _ = modules()
    pipeline.build(tmp_path)
    for name, frame in pipeline.generate(42).items():
        data = (tmp_path / f"synthetic/{name}.csv").read_bytes()
        assert b"\r" not in data
        assert data == frame.to_csv(index=False, lineterminator="\n").encode()
    assert b"\r" not in (tmp_path / "synthetic/provenance.json").read_bytes()
