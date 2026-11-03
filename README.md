# DataEngineerMarketdistribution
simply visualise the distribution or trend of Data engineer and Senior data engineer jobs around sydney market

## Dashboards
- Production: https://tiger13tiger.github.io/DataEngineerMarketdistribution/
- Staging (dev branch preview): https://tiger13tiger.github.io/DataEngineerMarketdistribution/dev/
- Delta trends (both environments, `/trends.html`): shows only the summary
  and trend of day-over-day changes — e.g.
  https://tiger13tiger.github.io/DataEngineerMarketdistribution/trends.html

All three are built and deployed automatically by GitHub Actions
(`.github/workflows/deploy.yml`) from the static site in `site/`, driven by
the data in `data/`.

## How data gets there

```
SEEK search API --extract--> bronze/ --transform--> staging/ --aggregate--> data/ (golden) --diff--> data/deltas/ --fetch--> dashboard + trends page
```

- `pipeline/extract_seek.py` — bronze: raw SEEK API responses.
- `pipeline/transform_staging.py` — staging: cleaned, deduplicated ad table.
- `pipeline/transform_golden.py` — golden: the `data/<id>.json` files the
  main dashboard reads.
- `pipeline/compute_delta.py` — delta: diffs each new golden snapshot
  against the previous one into `data/deltas/<date>.json`; `trends.html`
  reads only these, not the full snapshots.
- `.github/workflows/pipeline.yml` — runs all four steps daily (and on
  demand) and opens a PR into `dev` with the result, so every data update
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
- `data/deltas/` — the delta layer: one `{from, to, change}` diff per
  pipeline run (`manifest.json` lists them), read only by `trends.html`.
- `site/` — the static pages (plain HTML/CSS/JS + Chart.js via CDN):
  `index.html` is the main dashboard, `trends.html` is the delta-only
  summary/trend page.
- `scripts/` — `validate_data.py` (schema check) and `build_site.sh` (bundles
  `site/` + `data/` + `snapshots/` into a deployable folder), run by CI and
  by the deploy workflow.
