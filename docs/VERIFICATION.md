# Verification record

The final result and byte hashes are recorded in `PUBLICATION_MANIFEST.json`.
The complete byte-scan output is supplied separately with the delivery so it
does not recursively change the manifest's own hash.

Checks cover:

- Deterministic generation and all relational references.
- Warehouse creation and repeat builds.
- Partial delivery, complete/late delivery, overdue, and upcoming states.
- Empty filters, nonpositive capacity, invalid quantity, and missing columns.
- Every dashboard view, single-brand/supplier/category filters, CSV export
  control wiring, and startup without a pre-existing warehouse.
- Ruff formatting and lint checks.
- HTTP health endpoint of a separate local demo server.
- Byte-level credential, email, private-network, and machine-path patterns.
- Explicit publication allowlist and reachable Git blob/history checks.
- Independent deterministic recomputation of every published CSV.

No external source integration or production service was exercised. The scanner
is a heuristic check, supplemented by allowlisting, manual content review, and
the zero-reuse construction method. It is not an exhaustive secret detection
tool and cannot verify the ownership of arbitrary future contributions.

## Publishing from the user's normal terminal

If this session cannot publish, inspect the publication manifest first, then
run `publish_private.ps1` from the delivered checkout, using a Python environment
with the documented dependencies installed. It selects `charleszon`, verifies
the logged-in identity, runs the scan, requires a clean one-commit checkout,
creates a new private repository, verifies its ownership and privacy, and only
then pushes. It refuses an existing destination or configured remote.

The supplied ZIP intentionally excludes `.git`. If extracting the ZIP instead
of using the prepared checkout, initialize a fresh repository and create one
personal commit before running the publishing script:

```powershell
git init -b main
git config user.name charleszon
git config user.email '73291626+charleszon@users.noreply.github.com'
git add .
git commit -m 'Create independent synthetic supply chain portfolio'
.\publish_private.ps1
```
