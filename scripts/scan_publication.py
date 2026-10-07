import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWLIST = {
    ".gitignore",
    ".gitattributes",
    ".streamlit/config.toml",
    "README.md",
    "app.py",
    "requirements.txt",
    "requirements-dev.txt",
    "pyproject.toml",
    "demo/__init__.py",
    "demo/pipeline.py",
    "demo/analytics.py",
    "tests/test_demo.py",
    "scripts/scan_publication.py",
    "publish_private.ps1",
    "docs/METRICS.md",
    "docs/PROVENANCE.md",
    "docs/CASE_STUDY.md",
    "docs/VERIFICATION.md",
    "docs/PUBLICATION_MANIFEST.json",
    "data/synthetic/suppliers.csv",
    "data/synthetic/orders.csv",
    "data/synthetic/costs.csv",
    "data/synthetic/milestones.csv",
    "data/synthetic/schedule.csv",
    "data/synthetic/provenance.json",
}
PATTERNS = {
    "github_token": rb"(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})",
    "aws_key": rb"(?:AKIA|ASIA)[A-Z0-9]{16}",
    "private_key": rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    "google_key": rb"AIza[A-Za-z0-9_-]{30,}",
    "slack_token": rb"xox[baprs]-[A-Za-z0-9-]{20,}",
    "jwt": rb"eyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{15,}",
    "credential_assignment": rb"""(?i)(?:password|client_secret|access_token|api_key)\s*[:=]\s*["'][^"'\s]{8,}["']""",
    "credential_url": rb"https?://[^\s/@:]+:[^\s/@]+@",
    "private_network": rb"\b(?:10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.(?:1[6-9]|2\d|3[01])\.\d+\.\d+)\b",
    "personal_or_business_email": rb"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
    "windows_user_path": rb"(?i)[A-Z]:[\\/]Users[\\/]",
}


def git(*args):
    result = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace"))
    return result.stdout


def check_bytes(path, data, denied_terms=()):
    data.decode("utf-8")
    email_data = re.sub(
        rb"\b\d+\+[A-Za-z0-9-]+@users\.noreply\.github\.com\b", b"<public-github-noreply>", data
    )
    findings = [
        {"path": path, "rule": rule}
        for rule, expression in PATTERNS.items()
        if re.search(expression, email_data if rule == "personal_or_business_email" else data)
    ]
    if any(term.lower().encode() in data.lower() for term in denied_terms):
        findings.append({"path": path, "rule": "excluded_source_identifier"})
    return findings


def scan(denied_terms=()):
    findings = []
    entries = []
    for path in sorted(ALLOWLIST):
        full = ROOT / path
        if not full.is_file() or full.is_symlink():
            findings.append({"path": path, "rule": "missing_file_or_symlink"})
            continue
        data = full.read_bytes()
        findings.extend(check_bytes(path, data, denied_terms))
        entries.append(
            {"path": path, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        )
    provenance = json.loads((ROOT / "data/synthetic/provenance.json").read_text())
    if provenance.get("synthetic") is not True or provenance.get("seed") != 42:
        findings.append({"path": "data/synthetic/provenance.json", "rule": "provenance"})
    sys.path.insert(0, str(ROOT))
    from demo.pipeline import generate

    for name, frame in generate(42).items():
        if (ROOT / f"data/synthetic/{name}.csv").read_bytes() != frame.to_csv(
            index=False, lineterminator="\n"
        ).encode():
            findings.append({"path": f"data/synthetic/{name}.csv", "rule": "not_generated_fixture"})
    manifest = json.loads((ROOT / "docs/PUBLICATION_MANIFEST.json").read_text())
    expected_paths = ALLOWLIST - {"docs/PUBLICATION_MANIFEST.json"}
    if {entry["path"] for entry in manifest["contents"]} != expected_paths:
        findings.append({"path": "docs/PUBLICATION_MANIFEST.json", "rule": "manifest_paths"})
    for entry in manifest["contents"]:
        if entry["path"] not in expected_paths:
            continue
        content = (ROOT / entry["path"]).read_bytes()
        if hashlib.sha256(content).hexdigest() != entry["sha256"] or len(content) != entry["bytes"]:
            findings.append({"path": entry["path"], "rule": "manifest_mismatch"})
    tracked = set(git("ls-files", "-z").decode().split("\0")) - {""}
    for extra in sorted(tracked - ALLOWLIST):
        findings.append({"path": extra, "rule": "not_allowlisted"})
    object_lines = git("rev-list", "--objects", "--all").decode().splitlines()
    blobs = 0
    for line in object_lines:
        sha, _, path = line.partition(" ")
        if git("cat-file", "-t", sha).strip() != b"blob":
            continue
        blobs += 1
        if path not in ALLOWLIST:
            findings.append({"path": path, "rule": "historical_not_allowlisted"})
        findings.extend(check_bytes(path, git("cat-file", "blob", sha), denied_terms))
    count = int(git("rev-list", "--all", "--count"))
    status = git("status", "--porcelain", "--untracked-files=normal").decode()
    return {
        "result": "PASS" if not findings else "FAIL",
        "file_count": len(entries),
        "total_bytes": sum(e["bytes"] for e in entries),
        "reachable_commits": count,
        "historical_blobs_scanned": blobs,
        "findings": findings,
        "files": entries,
        "git_status": status,
        "limitations": "Heuristic pattern checks plus allowlist and synthetic provenance; manual review required.",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path)
    parser.add_argument("--denylist", type=Path)
    args = parser.parse_args()
    denied_terms = args.denylist.read_text().splitlines() if args.denylist else ()
    report = scan(denied_terms)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps({k: v for k, v in report.items() if k not in {"files", "git_status"}}, indent=2)
    )
    raise SystemExit(0 if report["result"] == "PASS" else 1)
