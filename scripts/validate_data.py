#!/usr/bin/env python3
"""Validate data/manifest.json and every snapshot it references. Used by CI and by deploy."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
REQUIRED_KEYS = {
    "id", "date", "source", "totals", "by_cloud", "work_type",
    "level", "skills_pct", "responsibilities_pct",
}


def fail(msg: str) -> None:
    print(f"::error::{msg}")
    sys.exit(1)


def main() -> None:
    manifest_path = DATA_DIR / "manifest.json"
    if not manifest_path.exists():
        fail(f"missing {manifest_path}")

    manifest = json.loads(manifest_path.read_text())
    snapshots = manifest.get("snapshots")
    if not snapshots:
        fail("manifest.json has no snapshots")

    for entry in snapshots:
        data_rel = entry.get("data")
        if not data_rel:
            fail(f"snapshot {entry.get('id')} has no 'data' path")

        data_path = ROOT / data_rel
        if not data_path.exists():
            fail(f"snapshot {entry['id']} references missing file {data_rel}")

        snapshot = json.loads(data_path.read_text())
        missing = REQUIRED_KEYS - snapshot.keys()
        if missing:
            fail(f"{data_rel} is missing required keys: {sorted(missing)}")

        report_rel = entry.get("report")
        if report_rel and not (ROOT / report_rel).exists():
            fail(f"snapshot {entry['id']} references missing report {report_rel}")

    print(f"validated {len(snapshots)} snapshot(s) OK")


if __name__ == "__main__":
    main()
