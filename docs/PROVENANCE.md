# Provenance and reuse boundary

This is an independently implemented portfolio demonstration of common supply
chain analytics concepts. No source code, configuration values, schemas,
datasets, screenshots, branding, assets, documentation, or commits were copied
from an employer repository. High-level domain concepts informed the selection
of demo views; all implementations and metric definitions were created afresh.

Data generation uses Python's pseudo-random generator with seed 42. The names
`Brand A` through `Brand C`, `Supplier 01` through `Supplier 08`, and `DEMO-PO-*`
and `DEMO-ST-*` identifiers have no mapping to any real records. Volumes, prices,
dates, capacity, and completion rates are chosen independently. No real rows
were anonymized, sampled, rescaled, scrambled, or used to calibrate the fixtures.

Publication is limited to the explicit file allowlist in
`scripts/scan_publication.py`. It includes new Python source, tests, generic
settings, documentation, and generated synthetic CSVs with their provenance.
The local warehouse, caches, temporary files, credentials, machine paths,
external source connections, and source repository history are excluded.

The repository starts with fresh history and is intended for a new **private**
repository owned by `charleszon`. Access to a work repository is not evidence of
permission to republish its contents. Keeping a repository private does not
justify transferring confidential material.

Future contributors must preserve this boundary. Repeat the byte and Git-history
scans after every change; do not replace the fixtures with real exports.
