#!/usr/bin/env python3
"""One-off diagnostic: fetch SEEK's actual search-results page (not a guessed
API) and report what's really there, so extract_seek.py can be fixed from
real findings instead of another blind guess.

This is throwaway tooling - run once via workflow_dispatch, read the
Actions log output, then delete it. Not part of the regular pipeline.
"""
import re

import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

URLS = [
    "https://www.seek.com.au/data-engineer-jobs/in-All-Sydney-NSW",
    "https://www.seek.com.au/jobs?keywords=data+engineer&where=All+Sydney+NSW",
]

MARKERS = [
    "__NEXT_DATA__",
    "window.SEEK_REDUX_DATA",
    "window.SK_DATA_LAYER",
    "apollo-state",
    "application/ld+json",
]


def main() -> None:
    for url in URLS:
        print(f"=== GET {url} ===")
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
        except Exception as exc:  # noqa: BLE001
            print(f"request failed: {exc}")
            continue

        print(f"status={resp.status_code} content-type={resp.headers.get('Content-Type')} len={len(resp.text)}")
        if resp.status_code != 200:
            print(resp.text[:1000])
            print()
            continue

        for marker in MARKERS:
            idx = resp.text.find(marker)
            print(f"marker {marker!r}: {'found at ' + str(idx) if idx != -1 else 'not found'}")

        api_paths = sorted(set(re.findall(r'"(/(?:api|graphql)[^"]{0,80})"', resp.text)))
        print(f"found {len(api_paths)} distinct api-ish paths (first 25):")
        for p in api_paths[:25]:
            print(" ", p)

        idx = resp.text.find("__NEXT_DATA__")
        if idx != -1:
            snippet = resp.text[idx : idx + 3000]
            print("--- __NEXT_DATA__ snippet (3000 chars) ---")
            print(snippet)

        idx = resp.text.find("application/ld+json")
        if idx != -1:
            snippet = resp.text[idx : idx + 2000]
            print("--- ld+json snippet (2000 chars) ---")
            print(snippet)

        print()


if __name__ == "__main__":
    main()
