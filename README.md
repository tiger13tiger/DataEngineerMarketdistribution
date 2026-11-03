# DataEngineerMarketdistribution
simply visualise the distribution or trend of Data engineer and Senior data engineer jobs around sydney market

## Dashboards
- Production: https://tiger13tiger.github.io/DataEngineerMarketdistribution/
- Staging (dev branch preview): https://tiger13tiger.github.io/DataEngineerMarketdistribution/dev/

Both are built and deployed automatically by GitHub Actions (`.github/workflows/deploy.yml`)
from the static site in `site/`, driven by the data in `data/`.

## How data gets there

```
SEEK search API --extract--> bronze/ --transform--> staging/ --aggregate--> data/ (golden) --fetch--> dashboard
```

- `pipeline/extract_seek.py` — bronze: raw SEEK API responses.
- `pipeline/transform_staging.py` — staging: cleaned, deduplicated ad table.
- `pipeline/transform_golden.py` — golden: the `data/<id>.json` files the
  dashboard reads.
- `.github/workflows/pipeline.yml` — runs the three steps on a schedule (and
  on demand) and opens a PR into `dev` with the result, so every data update
  still goes through CI + review like any other change.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full dev → main workflow, how
to add a snapshot by hand, and important caveats about the SEEK pipeline
before trusting the schedule.

## Snapshots
| Date | Ads | Highlights | Report | Data |
|---|---|---|---|---|
| 2 Nov 2026 | 75 (SEEK, All Sydney) | Azure-led (33 ads), 26% contract, median $165k; ICT vacancies −15.8% YoY | [sydney-de-market-2026-11.md](snapshots/sydney-de-market-2026-11.md) | [sydney-de-market-2026-11.json](data/sydney-de-market-2026-11.json) |

Later entries are added automatically by the pipeline above, or by hand per
`CONTRIBUTING.md`.

Sources: SEEK live ads (keyword-matched skills/responsibilities) and the JSA Internet Vacancy Index for monthly trend proxies.

## Repo layout
- `pipeline/` — the bronze → staging → golden extraction/transform scripts.
- `bronze/`, `staging/` — raw and intermediate pipeline output, kept for
  reproducibility/debugging.
- `snapshots/` — human-readable narrative report per hand-written snapshot.
- `data/` — the golden layer: structured metrics per snapshot
  (`manifest.json` lists them), read directly by the dashboard.
- `site/` — the static dashboard (plain HTML/CSS/JS + Chart.js via CDN).
- `scripts/` — `validate_data.py` (schema check) and `build_site.sh` (bundles
  `site/` + `data/` + `snapshots/` into a deployable folder), run by CI and
  by the deploy workflow.
