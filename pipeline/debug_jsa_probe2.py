#!/usr/bin/env python3
"""Second, wider throwaway probe: find JSA/data.gov.au's real IVI data path.

Round 1 found data.gov.au's classic CKAN path (/api/3/action/package_search)
404s (site rebuilt on Drupal) and jobsandskills.gov.au times out on a plain
GET. This round checks the data.gov.au homepage/robots/sitemap for the
current API path, tries an alternate CKAN mount point, and tries the old
pre-rebrand NSC/LMIP domain as a fallback, all with longer timeouts.
"""
import re

import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
    ),
}


def probe(url: str, timeout: int = 25) -> None:
    print(f"=== GET {url} ===")
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
    except Exception as exc:  # noqa: BLE001
        print(f"request failed: {exc}")
        print()
        return
    print(f"status={resp.status_code} final_url={resp.url} content-type={resp.headers.get('Content-Type')} len={len(resp.text)}")
    if resp.status_code == 200 and "json" in resp.headers.get("Content-Type", ""):
        print(resp.text[:800])
    elif resp.status_code != 200:
        print(resp.text[:300])
    print()


def find_api_hints(url: str) -> None:
    print(f"=== scanning {url} for api/data hints ===")
    try:
        resp = requests.get(url, headers=HEADERS, timeout=25)
    except Exception as exc:  # noqa: BLE001
        print(f"request failed: {exc}")
        print()
        return
    print(f"status={resp.status_code} len={len(resp.text)}")
    if resp.status_code != 200:
        print(resp.text[:300])
        print()
        return
    hints = sorted(set(re.findall(r'(?:href|src)="([^"]*(?:api|dataset|search)[^"]*)"', resp.text, re.I)))
    print(f"{len(hints)} hint link(s):")
    for h in hints[:40]:
        print(" ", h)
    print()


def main() -> None:
    find_api_hints("https://data.gov.au/")
    probe("https://data.gov.au/robots.txt")
    probe("https://data.gov.au/sitemap.xml")
    probe("https://data.gov.au/data/api/3/action/package_search?q=internet+vacancy+index")
    probe("https://www.lmip.gov.au/")
    probe("https://labourmarketinsights.gov.au/")


if __name__ == "__main__":
    main()
