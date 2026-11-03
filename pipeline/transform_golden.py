#!/usr/bin/env python3
"""Golden layer: aggregate staging/ads.csv into data/<id>.json + data/manifest.json.

This is the layer the dashboard actually reads (see site/app.js), so its
output schema must match the hand-built snapshots already in data/.
"""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"

SENIOR_LEVELS = {"Senior", "Lead/Architect", "Principal/Manager"}


def load_ads(staging_dir: Path) -> list:
    with (staging_dir / "ads.csv").open() as f:
        return list(csv.DictReader(f))


def pct_table(ads: list, field: str, label_key: str) -> tuple:
    sample = [a for a in ads if a["has_detail_text"] == "True"]
    n = len(sample)
    if n == 0:
        return [], 0

    counts = Counter()
    for ad in sample:
        for item in filter(None, ad[field].split(";")):
            counts[item] += 1

    table = [
        {label_key: k, "pct": round(100 * v / n)}
        for k, v in sorted(counts.items(), key=lambda kv: -kv[1])
    ]
    return table, n


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--staging-dir", required=True)
    parser.add_argument("--run-date", required=True)
    args = parser.parse_args()

    ads = load_ads(Path(args.staging_dir))
    if not ads:
        raise SystemExit("no ads in staging; aborting golden build")

    run_id = f"seek-sydney-de-market-{args.run_date}"

    level_counts = Counter(a["level"] for a in ads)
    cloud_counts = Counter()
    for ad in ads:
        clouds = list(filter(None, ad["cloud"].split(";"))) if ad["cloud"] != "None" else []
        if not clouds:
            cloud_counts["No cloud named"] += 1
        for c in clouds:
            cloud_counts[c] += 1

    totals = {
        "ads": len(ads),
        "senior_plus": sum(1 for a in ads if a["level"] in SENIOR_LEVELS),
        "mid_junior": sum(1 for a in ads if a["level"] not in SENIOR_LEVELS),
    }
    work_type_counts = Counter(a["work_type"] for a in ads)
    contract = work_type_counts.get("Contract", 0)

    skills_pct, skills_sample = pct_table(ads, "skills", "skill")
    resp_pct, resp_sample = pct_table(ads, "responsibilities", "responsibility")

    snapshot = {
        "id": run_id,
        "date": args.run_date,
        "source": "SEEK live ads, All Sydney NSW (automated pipeline)",
        "totals": totals,
        "by_cloud": [
            {"cloud": k, "ads": v, "senior_plus": None} for k, v in cloud_counts.most_common()
        ],
        "work_type": {
            "full_time": work_type_counts.get("Full time", 0),
            "contract": contract,
            "contract_pct": round(100 * contract / len(ads)) if ads else 0,
        },
        "level": [{"level": k, "ads": v} for k, v in level_counts.items()],
        "salary": {"median_aud": None, "sample_size": 0, "min_aud": None, "max_aud": None},
        "weekly_postings": [],
        "skills_pct": skills_pct,
        "responsibilities_pct": resp_pct,
        "monthly_trend": None,
        "methodology": (
            f"Automated pipeline: SEEK search API, with {skills_sample} ad detail page(s) "
            "fetched for skill/responsibility keyword matching (rest counted by title/teaser "
            "only). Salary and the JSA monthly-vacancy trend are not yet computed by the "
            "automated pipeline."
        ),
    }

    DATA_DIR.mkdir(exist_ok=True)
    (DATA_DIR / f"{run_id}.json").write_text(json.dumps(snapshot, indent=2) + "\n")

    manifest_path = DATA_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {"snapshots": []}
    manifest["snapshots"] = [s for s in manifest["snapshots"] if s["id"] != run_id]
    manifest["snapshots"].append(
        {
            "id": run_id,
            "date": args.run_date,
            "title": f"Sydney Data Engineer market snapshot — {args.run_date} (automated)",
            "report": None,
            "data": f"data/{run_id}.json",
        }
    )
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    print(f"wrote {run_id} ({totals['ads']} ads, {skills_sample} with detail text)")


if __name__ == "__main__":
    main()
