#!/usr/bin/env python3
"""Delta layer: diff the two most recent automated golden snapshots into data/deltas/<date>.json.

Run after transform_golden.py in the pipeline. No-ops (prints a message,
exit 0) when fewer than two snapshots exist yet - there's nothing to diff
on the very first run ever.
"""
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
DELTAS_DIR = DATA_DIR / "deltas"


def load_snapshot(data_rel: str) -> dict:
    return json.loads((REPO_ROOT / data_rel).read_text())


def counter_delta(prev_rows: list, curr_rows: list, key_field: str, value_field: str) -> list:
    prev = {r[key_field]: r[value_field] for r in prev_rows}
    curr = {r[key_field]: r[value_field] for r in curr_rows}
    keys = sorted(set(prev) | set(curr))
    return [
        {
            key_field: k,
            "from": prev.get(k, 0),
            "to": curr.get(k, 0),
            "change": curr.get(k, 0) - prev.get(k, 0),
        }
        for k in keys
    ]


def scalar_delta(prev_val, curr_val) -> dict:
    return {"from": prev_val, "to": curr_val, "change": curr_val - prev_val}


def main() -> None:
    manifest_path = DATA_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    # Only diff like with like: hand-built snapshots use different scope and
    # full-text matching, so diffing them against automated runs shows fake moves.
    snapshots = [
        s for s in manifest.get("snapshots", [])
        if "automated pipeline" in load_snapshot(s["data"]).get("source", "")
    ]

    if len(snapshots) < 2:
        print("fewer than 2 automated snapshots exist; nothing to diff yet, skipping delta")
        return

    prev_entry, curr_entry = snapshots[-2], snapshots[-1]
    prev = load_snapshot(prev_entry["data"])
    curr = load_snapshot(curr_entry["data"])

    delta = {
        "date": curr_entry["date"],
        "from_id": prev_entry["id"],
        "to_id": curr_entry["id"],
        "totals": {
            "ads": scalar_delta(prev["totals"]["ads"], curr["totals"]["ads"]),
            "senior_plus": scalar_delta(prev["totals"]["senior_plus"], curr["totals"]["senior_plus"]),
            "mid_junior": scalar_delta(prev["totals"]["mid_junior"], curr["totals"]["mid_junior"]),
        },
        "work_type": {
            "contract_pct": scalar_delta(prev["work_type"]["contract_pct"], curr["work_type"]["contract_pct"]),
        },
        "by_cloud": counter_delta(prev["by_cloud"], curr["by_cloud"], "cloud", "ads"),
        "level": counter_delta(prev["level"], curr["level"], "level", "ads"),
    }

    DELTAS_DIR.mkdir(parents=True, exist_ok=True)
    delta_path = DELTAS_DIR / f"{curr_entry['date']}.json"
    delta_path.write_text(json.dumps(delta, indent=2) + "\n")

    deltas_manifest_path = DELTAS_DIR / "manifest.json"
    deltas_manifest = (
        json.loads(deltas_manifest_path.read_text())
        if deltas_manifest_path.exists()
        else {"deltas": []}
    )
    deltas_manifest["deltas"] = [
        d for d in deltas_manifest["deltas"] if d["date"] != curr_entry["date"]
    ]
    deltas_manifest["deltas"].append(
        {
            "date": curr_entry["date"],
            "from": prev_entry["id"],
            "to": curr_entry["id"],
            "file": f"data/deltas/{curr_entry['date']}.json",
        }
    )
    deltas_manifest_path.write_text(json.dumps(deltas_manifest, indent=2) + "\n")

    print(f"wrote delta {curr_entry['date']}: ads change {delta['totals']['ads']['change']:+d}")


if __name__ == "__main__":
    main()
