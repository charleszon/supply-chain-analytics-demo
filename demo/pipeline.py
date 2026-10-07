import argparse
import json
import os
import random
from datetime import date, timedelta
from pathlib import Path

import duckdb
import pandas as pd

AS_OF = pd.Timestamp("2026-07-15")
ROOT = Path(__file__).resolve().parents[1]
DATE_COLUMNS = {
    "orders": ["order_date", "due_date", "delivered_date"],
    "milestones": ["planned_date", "completed_date"],
    "schedule": ["start_date", "end_date"],
}
REQUIRED = {
    "suppliers": ["supplier_id", "supplier", "monthly_capacity"],
    "orders": [
        "order_id",
        "supplier_id",
        "brand",
        "category",
        "quantity",
        "delivered_quantity",
        "order_date",
        "due_date",
        "delivered_date",
    ],
    "costs": ["order_id", "material", "labor", "overhead", "target"],
    "milestones": ["order_id", "stage", "planned_date", "completed_date"],
    "schedule": ["order_id", "line", "start_date", "end_date"],
}


def data_dir():
    return Path(os.environ.get("DEMO_DATA_DIR", ROOT / "var" / "demo"))


def generate(seed=42):
    rng = random.Random(seed)
    suppliers = pd.DataFrame(
        [
            {
                "supplier_id": f"SUP{i:03d}",
                "supplier": f"Supplier {i:02d}",
                "monthly_capacity": rng.randint(12, 25) * 1000,
                "lead_time_days": rng.randint(35, 70),
            }
            for i in range(1, 9)
        ]
    )
    orders, costs, milestones, schedules = [], [], [], []
    base_costs = {"Tops": 70000, "Bottoms": 110000, "Outerwear": 190000}
    stages = [("Development", 75), ("Sample", 55), ("Approval", 35), ("Production ready", 20)]
    for i in range(360):
        supplier = suppliers.iloc[rng.randrange(len(suppliers))]
        due = date(2026, 1, 1) + timedelta(days=rng.randrange(365))
        category = rng.choice(list(base_costs))
        qty = rng.randint(4, 40) * 100
        delivered = None
        delivered_qty = 0
        if due <= AS_OF.date():
            candidate = due + timedelta(days=rng.randint(-8, 22))
            if candidate <= AS_OF.date() and rng.random() < 0.85:
                delivered = candidate
                delivered_qty = qty if rng.random() < 0.88 else qty // 2
        order_id = f"DEMO-PO-{i + 1:04d}"
        orders.append(
            {
                "order_id": order_id,
                "style": f"DEMO-ST-{i % 80 + 1:03d}",
                "supplier_id": supplier["supplier_id"],
                "brand": rng.choice(["Brand A", "Brand B", "Brand C"]),
                "category": category,
                "quantity": qty,
                "delivered_quantity": delivered_qty,
                "order_date": due - timedelta(days=int(supplier["lead_time_days"]) + 20),
                "due_date": due,
                "delivered_date": delivered,
                "retail_price": base_costs[category] * 3,
            }
        )
        baseline = base_costs[category]
        costs.append(
            {
                "order_id": order_id,
                "material": round(baseline * rng.uniform(0.45, 0.65)),
                "labor": round(baseline * rng.uniform(0.18, 0.30)),
                "overhead": round(baseline * rng.uniform(0.10, 0.20)),
                "target": baseline,
            }
        )
        start = due - timedelta(days=rng.randint(18, 35))
        schedules.append(
            {
                "order_id": order_id,
                "line": f"{supplier['supplier_id']}-L{rng.randint(1, 3)}",
                "start_date": start,
                "end_date": due - timedelta(days=3),
            }
        )
        for stage, offset in stages:
            planned = due - timedelta(days=offset)
            completed = planned + timedelta(days=rng.randint(-4, 15))
            if completed > AS_OF.date() or rng.random() < 0.12:
                completed = None
            milestones.append(
                {
                    "order_id": order_id,
                    "stage": stage,
                    "planned_date": planned,
                    "completed_date": completed,
                }
            )
    tables = {
        "suppliers": suppliers,
        "orders": pd.DataFrame(orders),
        "costs": pd.DataFrame(costs),
        "milestones": pd.DataFrame(milestones),
        "schedule": pd.DataFrame(schedules),
    }
    for name, cols in DATE_COLUMNS.items():
        for col in cols:
            tables[name][col] = pd.to_datetime(tables[name][col])
    return tables


def validate(tables):
    for name, required in REQUIRED.items():
        if name not in tables:
            raise ValueError(f"Missing table: {name}")
        missing = set(required) - set(tables[name])
        if missing:
            raise ValueError(f"{name}: missing columns {sorted(missing)}")
    orders = tables["orders"]
    suppliers = tables["suppliers"]
    if not suppliers["supplier_id"].is_unique or not orders["order_id"].is_unique:
        raise ValueError("Duplicate supplier or order identifiers")
    if not orders["quantity"].gt(0).all():
        raise ValueError("Order quantity must be positive")
    if not (
        orders["delivered_quantity"].ge(0) & orders["delivered_quantity"].le(orders["quantity"])
    ).all():
        raise ValueError("Invalid delivered quantity")
    if not suppliers["monthly_capacity"].gt(0).all():
        raise ValueError("Supplier capacity must be positive")
    if not orders["supplier_id"].isin(suppliers["supplier_id"]).all():
        raise ValueError("Unknown supplier reference")
    for name in ["costs", "milestones", "schedule"]:
        if not tables[name]["order_id"].isin(orders["order_id"]).all():
            raise ValueError(f"{name}: unknown order reference")
    if not tables["costs"][["material", "labor", "overhead", "target"]].gt(0).all().all():
        raise ValueError("Cost values must be positive")
    if not orders["due_date"].ge(orders["order_date"]).all():
        raise ValueError("Due date precedes order date")
    if not tables["schedule"]["end_date"].ge(tables["schedule"]["start_date"]).all():
        raise ValueError("Schedule end precedes start")


def build(directory=None, seed=42):
    directory = Path(directory) if directory is not None else data_dir()
    directory.mkdir(parents=True, exist_ok=True)
    tables = generate(seed)
    validate(tables)
    synthetic = directory / "synthetic"
    synthetic.mkdir(exist_ok=True)
    with duckdb.connect(str(directory / "warehouse.duckdb")) as conn:
        for name, frame in tables.items():
            frame.to_csv(synthetic / f"{name}.csv", index=False, lineterminator="\n")
            conn.register("frame", frame)
            conn.execute(f'CREATE OR REPLACE TABLE "{name}" AS SELECT * FROM frame')
            conn.unregister("frame")
    (synthetic / "provenance.json").write_text(
        json.dumps(
            {
                "synthetic": True,
                "seed": seed,
                "as_of": AS_OF.date().isoformat(),
                "source": "Independent random generation; no real records or source files",
                "row_counts": {name: len(frame) for name, frame in tables.items()},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return tables


def load(directory=None):
    directory = Path(directory) if directory is not None else data_dir()
    db = directory / "warehouse.duckdb"
    if not db.exists():
        build(directory)
    with duckdb.connect(str(db), read_only=True) as conn:
        return {name: conn.execute(f'SELECT * FROM "{name}"').df() for name in REQUIRED}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build the synthetic demo warehouse")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    result = build(args.output, args.seed)
    print(json.dumps({name: len(frame) for name, frame in result.items()}))
