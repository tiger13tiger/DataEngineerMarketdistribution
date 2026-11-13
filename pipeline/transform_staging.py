#!/usr/bin/env python3
"""Staging layer: parse bronze SEEK responses into a clean, deduplicated ad table.

Search-result teasers are short, so skills/responsibilities keyword matching
is only reliable for ads whose full detail page text was fetched
(--detail-fetch-limit). That's capped and rate-limited by default to keep
the scraping footprint small; raise it for a more complete sample at the
cost of more requests per run.
"""
import argparse
import csv
import json
import random
import re
import sys
import time
from pathlib import Path

import requests

USER_AGENT = (
    "Mozilla/5.0 (compatible; DataEngineerMarketdistribution-pipeline/1.0; "
    "+https://github.com/tiger13tiger/DataEngineerMarketdistribution)"
)

SENIOR_TITLE_PAT = re.compile(r"senior|lead|principal|staff", re.I)
MANAGER_TITLE_PAT = re.compile(r"manager|head of|architect", re.I)
JUNIOR_TITLE_PAT = re.compile(r"junior|graduate|entry level", re.I)

CLOUD_PATTERNS = {
    "Azure": re.compile(r"azure", re.I),
    "AWS": re.compile(r"\baws\b|amazon web services", re.I),
    "GCP": re.compile(r"\bgcp\b|google cloud", re.I),
}

SKILL_PATTERNS = {
    "SQL": re.compile(r"\bsql\b", re.I),
    "Python/PySpark": re.compile(r"python|pyspark", re.I),
    "Snowflake": re.compile(r"snowflake", re.I),
    "Databricks": re.compile(r"databricks", re.I),
    "dbt": re.compile(r"\bdbt\b", re.I),
    "Spark": re.compile(r"\bspark\b", re.I),
    "Kafka/streaming": re.compile(r"kafka|streaming", re.I),
    "Terraform/IaC": re.compile(r"terraform|infrastructure as code", re.I),
    "Airflow": re.compile(r"airflow", re.I),
    "Power BI": re.compile(r"power ?bi", re.I),
    "Tableau": re.compile(r"tableau", re.I),
    "Docker/K8s": re.compile(r"docker|kubernetes|k8s", re.I),
}

RESPONSIBILITY_PATTERNS = {
    "Pipelines ETL/ELT": re.compile(r"pipeline|etl|elt", re.I),
    "Monitoring & support": re.compile(r"monitor|on-call|support", re.I),
    "Data quality/governance/security": re.compile(r"governance|data quality|security", re.I),
    "Platform architecture": re.compile(r"architecture|platform design", re.I),
    "Stakeholder collaboration": re.compile(r"stakeholder|collaborat", re.I),
    "Enable BI/reporting": re.compile(r"\bbi\b|reporting|dashboard", re.I),
    "CI/CD & DevOps": re.compile(r"ci/cd|devops|continuous integration", re.I),
    "Mentoring/leading": re.compile(r"mentor|lead(ing|ership)", re.I),
}


def level_for(title: str) -> str:
    if MANAGER_TITLE_PAT.search(title):
        return "Principal/Manager"
    if SENIOR_TITLE_PAT.search(title):
        return "Senior"
    if JUNIOR_TITLE_PAT.search(title):
        return "Junior"
    return "Mid"


def load_jobs(bronze_dir: Path) -> list:
    jobs = {}
    for path in sorted(bronze_dir.glob("*.json")):
        if path.name == "_manifest.json":
            continue
        payload = json.loads(path.read_text())
        for job in payload.get("data") or payload.get("jobs") or []:
            job_id = job.get("id") or job.get("jobId")
            if job_id is None or job_id in jobs:
                continue
            jobs[job_id] = job
    return list(jobs.values())


def fetch_detail_text(job_id: str) -> str:
    url = f"https://www.seek.com.au/job/{job_id}"
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=20)
    resp.raise_for_status()
    return resp.text


def matches(patterns: dict, text: str) -> list:
    return [name for name, pat in patterns.items() if pat.search(text)]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bronze-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument(
        "--detail-fetch-limit",
        type=int,
        default=0,
        help="Max ads to fetch full detail text for (skills/responsibilities match). 0 = skip.",
    )
    args = parser.parse_args()

    bronze_dir = Path(args.bronze_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    jobs = load_jobs(bronze_dir)
    if not jobs:
        print("::error::No jobs parsed from bronze data; aborting.")
        sys.exit(1)

    rows = []
    for i, job in enumerate(jobs):
        title = job.get("title", "") or ""
        teaser = job.get("teaser", "") or ""
        text_for_matching = f"{title} {teaser}"
        detail_text = ""

        if i < args.detail_fetch_limit:
            job_id = job.get("id") or job.get("jobId")
            try:
                detail_text = fetch_detail_text(job_id)
                text_for_matching += " " + detail_text
                time.sleep(random.uniform(1.5, 3.0))
            except Exception as exc:  # noqa: BLE001
                print(f"::warning::failed to fetch detail for job {job_id}: {exc}")

        cloud = matches(CLOUD_PATTERNS, text_for_matching)
        skills = matches(SKILL_PATTERNS, text_for_matching)
        responsibilities = matches(RESPONSIBILITY_PATTERNS, text_for_matching)
        work_type = (job.get("workType") or job.get("workTypes") or job.get("worktype") or "")  # v5: workTypes list
        if isinstance(work_type, list):
            work_type = " ".join(work_type)

        rows.append(
            {
                "id": job.get("id") or job.get("jobId"),
                "title": title,
                "level": level_for(title),
                "work_type": "Contract" if "contract" in work_type.lower() else "Full time",
                "cloud": ";".join(cloud) or "None",
                "skills": ";".join(skills),
                "responsibilities": ";".join(responsibilities),
                "listing_date": job.get("listingDate") or job.get("listingDateDisplay") or "",
                "salary_label": job.get("salaryLabel") or job.get("salaryLabelFull") or job.get("salary") or "",
                "has_detail_text": bool(detail_text),
            }
        )

    out_path = out_dir / "ads.csv"
    with out_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"staged {len(rows)} ad(s) into {out_path}")


if __name__ == "__main__":
    main()
