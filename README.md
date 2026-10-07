# Supply Chain Analytics — synthetic portfolio

A runnable demonstration of supply chain dashboards for a fictional retail
business. **Every record, brand, supplier, price, and capacity is synthetic.**
The project was written independently; it contains no employer code, assets,
exports, database, integrations, credentials, or Git history.

## What a client can explore

- Delivery: complete, late, overdue, and upcoming orders; partial receipts.
- Capacity: monthly allocations, utilization, and overloaded supplier-months.
- Costing: material/labor/overhead, unit costs, targets, and variance.
- Cost simulator: compare a quote with fictional comparable orders.
- Production: supplier line schedules with visible overlapping slots.
- Milestones: development completion and overdue stages.
- Supplier intelligence: delivery performance and allocation footprint.
- Overview: planned volume, receipt rate, and orders needing attention.

Brand, supplier, category, and due-month filters apply across the eight views.
Filtered orders can be exported to CSV. The demo does not connect to any real
source system and does not accept uploads of business data.

## Run locally

Requires Python 3.13+. Commands below run from the project directory.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m demo.pipeline
python -m streamlit run app.py
```

Open `http://127.0.0.1:8501`. The app automatically generates the demo warehouse
if it is absent. To recreate it, run `python -m demo.pipeline` again. Generated
local files live in ignored `var/demo/`. This command replaces only the demo
tables in the selected output database. It must never target a business database.

macOS/Linux: use `python3 -m venv .venv` and `source .venv/bin/activate`, then the
same Python commands. The checked-in synthetic CSVs are reference outputs;
the local warehouse is rebuilt independently from the deterministic generator.

## Architecture

`demo/pipeline.py` generates five relational datasets, validates them, and writes
CSV outputs and DuckDB tables. `demo/analytics.py` computes generic metrics.
`app.py` reads the warehouse and presents the dashboard. Generated database and
temporary test outputs are excluded from Git.

The fixed snapshot is **15 July 2026**, with random seed **42**. The fixture has
360 purchase orders, eight suppliers, three brands, three categories, 360 cost
records, 360 production slots, and 1,440 milestones. It includes partial
deliveries, late deliveries, uncompleted orders, and overloaded planning periods.
These distributions were chosen independently for demonstration, without fitting
them to any business data.

## Verification

```powershell
python -m pip install -r requirements-dev.txt
New-Item -ItemType Directory -Force var/pytest-temp | Out-Null
python -m pytest -q -p no:cacheprovider --basetemp=var/pytest-temp/run
python -m ruff check --no-cache .
python scripts/scan_publication.py
```

On macOS/Linux replace the `New-Item` command with `mkdir -p var/pytest-temp`.
Tests cover generation, relationships, validation, metric boundaries, all eight
dashboard views, filters, and export wiring. The publication scanner checks the
allowlisted files and reachable Git blobs. It is a local heuristic scan, not a
guarantee that arbitrary future edits are safe. Add an independent secret scanner
and repeat a manual content review before making later versions public.

See [metric definitions](docs/METRICS.md), [data provenance](docs/PROVENANCE.md),
[case study](docs/CASE_STUDY.md), and [publication manifest](docs/PUBLICATION_MANIFEST.json).
