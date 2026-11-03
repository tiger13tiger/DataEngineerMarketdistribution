#!/usr/bin/env python3
"""Bronze layer: pull raw Data Engineer job ad search results from SEEK.

This targets SEEK's public search page's backing JSON endpoint. That
endpoint is NOT an official/documented API - it was reverse-engineered
from the website and can change or start blocking datacenter IPs (like
GitHub Actions runners) without notice. Always verify with a manual
`workflow_dispatch` run and inspect the bronze/ output before trusting
the schedule.

Usage:
    python pipeline/extract_seek.py --out-dir bronze/seek/2026-11-09
"""
import argparse
import json
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

SEARCH_URL = "https://www.seek.com.au/api/chalice-search/v4/search"
USER_AGENT = (
    "Mozilla/5.0 (compatible; DataEngineerMarketdistribution-pipeline/1.0; "
    "+https://github.com/tiger13tiger/DataEngineerMarketdistribution)"
)
KEYWORDS = [
    "data engineer",
    "senior data engineer",
    "lead data engineer",
    "principal data engineer",
]
WHERE = "All Sydney NSW"
PAGE_SIZE = 22
MAX_PAGES_PER_KEYWORD = 5
REQUEST_DELAY_RANGE = (1.5, 3.0)


def fetch_page(keyword: str, page: int, out_dir: Path) -> dict:
    params = {
        "keywords": keyword,
        "where": WHERE,
        "page": page,
        "pageSize": PAGE_SIZE,
        "siteKey": "AU-Main",
        "sourcesystem": "houston",
    }
    resp = requests.get(
        SEARCH_URL,
        params=params,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        timeout=20,
    )

    if not resp.ok or "json" not in resp.headers.get("Content-Type", ""):
        # Save exactly what SEEK sent back so a failure is debuggable from
        # the Action's artifact/log instead of a bare "request failed".
        dump_path = out_dir / f"_failure_{slugify(keyword)}_page{page}.txt"
        dump_path.write_text(
            f"GET {resp.url}\n"
            f"status: {resp.status_code}\n"
            f"content-type: {resp.headers.get('Content-Type')}\n"
            f"headers: {dict(resp.headers)}\n\n"
            f"body (first 2000 chars):\n{resp.text[:2000]}"
        )
        raise RuntimeError(
            f"HTTP {resp.status_code}, content-type={resp.headers.get('Content-Type')!r} "
            f"(saved full response to {dump_path.name}). This usually means the endpoint "
            f"changed, requires different params/headers, or is blocking this runner's IP."
        )

    try:
        return resp.json()
    except ValueError as exc:
        raise RuntimeError(f"response claimed JSON but failed to parse: {exc}") from exc


def slugify(text: str) -> str:
    return text.lower().replace(" ", "-")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    fetched = []
    errors = []

    for keyword in KEYWORDS:
        for page in range(1, MAX_PAGES_PER_KEYWORD + 1):
            try:
                payload = fetch_page(keyword, page, out_dir)
            except Exception as exc:  # noqa: BLE001 - record and move to next keyword
                errors.append({"keyword": keyword, "page": page, "error": str(exc)})
                print(f"::error::[{keyword!r} page {page}] {exc}")
                break

            out_path = out_dir / f"{slugify(keyword)}_page{page}.json"
            out_path.write_text(json.dumps(payload, indent=2))
            fetched.append(str(out_path))

            jobs = payload.get("data") or payload.get("jobs") or []
            if len(jobs) < PAGE_SIZE:
                break  # last page for this keyword

            time.sleep(random.uniform(*REQUEST_DELAY_RANGE))

    manifest = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "keywords": KEYWORDS,
        "where": WHERE,
        "files": fetched,
        "errors": errors,
    }
    (out_dir / "_manifest.json").write_text(json.dumps(manifest, indent=2))

    if not fetched:
        print("::error::No pages fetched successfully; aborting pipeline run.")
        sys.exit(1)

    if errors:
        print(f"::warning::{len(errors)} request(s) failed; see _manifest.json")

    print(f"fetched {len(fetched)} page(s) into {out_dir}")


if __name__ == "__main__":
    main()
