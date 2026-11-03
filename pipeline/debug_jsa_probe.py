#!/usr/bin/env python3
"""One-off diagnostic: find JSA's actual Internet Vacancy Index data endpoint.

Throwaway - run once via workflow_dispatch, read the Actions log, then
delete it. Tries the data.gov.au CKAN API (documented, stable, meant for
programmatic access) and the jobsandskills.gov.au page itself as a fallback.
"""
import json
import re

import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
    ),
}


def try_ckan_search(query: str) -> None:
    url = "https://data.gov.au/api/3/action/package_search"
    print(f"=== CKAN package_search: {query!r} ===")
    try:
        resp = requests.get(url, params={"q": query, "rows": 10}, headers=HEADERS, timeout=20)
    except Exception as exc:  # noqa: BLE001
        print(f"request failed: {exc}")
        return
    print(f"status={resp.status_code} content-type={resp.headers.get('Content-Type')}")
    if resp.status_code != 200:
        print(resp.text[:500])
        return
    data = resp.json()
    results = data.get("result", {}).get("results", [])
    print(f"{len(results)} package(s) found")
    for pkg in results:
        print(f"- {pkg.get('title')!r} (name={pkg.get('name')})")
        for res in pkg.get("resources", []):
            print(f"    resource: {res.get('name')!r} format={res.get('format')} url={res.get('url')}")
    print()


def try_page(url: str) -> None:
    print(f"=== GET {url} ===")
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
    except Exception as exc:  # noqa: BLE001
        print(f"request failed: {exc}")
        return
    print(f"status={resp.status_code} content-type={resp.headers.get('Content-Type')} len={len(resp.text)}")
    if resp.status_code != 200:
        print(resp.text[:500])
        print()
        return

    links = sorted(set(re.findall(r'href="([^"]+\.(?:xlsx|xls|csv|zip))"', resp.text, re.I)))
    print(f"found {len(links)} file link(s):")
    for link in links[:30]:
        print(" ", link)
    print()


def main() -> None:
    try_ckan_search("internet vacancy index")
    try_ckan_search("IVI occupation")
    try_page("https://www.jobsandskills.gov.au/data/internet-vacancy-index")
    try_page("https://www.jobsandskills.gov.au/data/vacancy-report")


if __name__ == "__main__":
    main()
