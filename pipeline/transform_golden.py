#!/usr/bin/env python3
"""Golden layer: aggregate staging/ads.csv into data/<id>.json + data/manifest.json.

This is the layer the dashboard actually reads (see site/app.js), so its
output schema must match the hand-built snapshots already in data/.
"""
import argparse
import csv
import json
import re
import statistics
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"

SENIOR_LEVELS = {"Senior", "Lead/Architect", "Principal/Manager"}


def load_ads(staging_dir: Path) -> list:
    with (staging_dir / "ads.csv").open() as f:
        return list(csv.DictReader(f))


def has_rich_text(ad: dict) -> bool:
    # full detail page, or v5 bulletPoints (stack is usually listed there)
    return ad.get("text_source", "detail" if ad["has_detail_text"] == "True" else "teaser") != "teaser"


def pct_table(ads: list, field: str, label_key: str) -> tuple:
    sample = [a for a in ads if has_rich_text(a)]
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


AMOUNT_PAT = re.compile(r"\$?\s*(\d{2,3}(?:,\d{3})+|\d{2,3}(?:\.\d+)?\s*[kK])")


def annual_salary(label: str):
    """Midpoint of an annual AUD salary label; None for day/hour rates or unparseable."""
    if not label or re.search(r"per (day|hour)|p/?d|p/?h|daily|hourly|/ ?(day|hr|hour)", label, re.I):
        return None
    vals = []
    for m in AMOUNT_PAT.findall(label):
        m = m.replace(",", "").replace(" ", "")
        v = float(m[:-1]) * 1000 if m[-1] in "kK" else float(m)
        if 40_000 <= v <= 500_000:
            vals.append(v)
    return round(sum(vals) / len(vals)) if vals else None


def salary_summary(ads: list) -> dict:
    vals = [v for v in (annual_salary(a.get("salary_label", "")) for a in ads) if v]
    if not vals:
        return {"median_aud": None, "sample_size": 0, "min_aud": None, "max_aud": None}
    return {
        "median_aud": round(statistics.median(vals) / 1000) * 1000,
        "sample_size": len(vals),
        "min_aud": min(vals),
        "max_aud": max(vals),
    }


def weekly_postings(ads: list) -> list:
    weeks = Counter()
    for a in ads:
        try:
            d = date.fromisoformat(a["listing_date"][:10])
        except ValueError:
            continue
        weeks[(d - timedelta(days=d.weekday())).isoformat()] += 1  # Monday week start
    return [{"week_start": k, "ads": v} for k, v in sorted(weeks.items())]


def latest_monthly_trend(manifest: dict):
    """JSA vacancy trend isn't scraped; carry forward the newest one so the dashboard keeps it."""
    for entry in reversed(manifest.get("snapshots", [])):
        path = REPO_ROOT / entry["data"]
        if not path.exists():
            continue
        trend = json.loads(path.read_text()).get("monthly_trend")
        if trend:
            trend = dict(trend)
            base = trend.get("note", "").split(" [Carried forward")[0]
            trend["note"] = f"{base} [Carried forward from snapshot {entry['id']}; update when JSA publishes a new month.]".strip()
            return trend
    return None


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

    manifest_path = DATA_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {"snapshots": []}
    manifest["snapshots"] = [s for s in manifest["snapshots"] if s["id"] != run_id]

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
        "salary": salary_summary(ads),
        "weekly_postings": weekly_postings(ads),
        "skills_pct": skills_pct,
        "responsibilities_pct": resp_pct,
        "monthly_trend": latest_monthly_trend(manifest),
        "methodology": (
            f"Automated pipeline: SEEK search API, DE-type titles only. Skills/responsibilities "
            f"% are over the {skills_sample} ad(s) with a full detail page or SEEK bullet points "
            "(title + teaser + bullets keyword match; shorter than full ad text, so shares run "
            "lower than the hand-built snapshots). Cloud counts use the same text. Salary is the "
            "median of annual ranges stated in search results (day rates excluded). The JSA "
            "monthly-vacancy trend is carried forward from the latest snapshot that has it."
        ),
    }

    DATA_DIR.mkdir(exist_ok=True)
    (DATA_DIR / f"{run_id}.json").write_text(json.dumps(snapshot, indent=2) + "\n")

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

    print(f"wrote {run_id} ({totals['ads']} ads, {skills_sample} with detail/bullet text)")


if __name__ == "__main__":
    main()
