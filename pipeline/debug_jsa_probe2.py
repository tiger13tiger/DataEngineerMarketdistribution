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


def dump_resources(package_name: str) -> None:
    url = f"https://data.gov.au/data/api/3/action/package_show?id={package_name}"
    print(f"=== package_show: {package_name} ===")
    try:
        resp = requests.get(url, headers=HEADERS, timeout=25)
    except Exception as exc:  # noqa: BLE001
        print(f"request failed: {exc}")
        print()
        return
    print(f"status={resp.status_code}")
    if resp.status_code != 200:
        print(resp.text[:500])
        print()
        return
    data = resp.json()
    result = data.get("result", {})
    print(f"title: {result.get('title')}")
    print(f"notes: {(result.get('notes') or '')[:500]}")
    resources = result.get("resources", [])
    print(f"{len(resources)} resource(s):")
    for res in resources:
        print(f"  - name={res.get('name')!r} format={res.get('format')} last_modified={res.get('last_modified') or res.get('created')}")
        print(f"    url={res.get('url')}")
    print()


def main() -> None:
    dump_resources("internet-vacancy-index")


if __name__ == "__main__":
    main()
