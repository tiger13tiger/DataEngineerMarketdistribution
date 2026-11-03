# DataEngineerMarketdistribution
simply visualise the distribution or trend of Data engineer and Senior data engineer jobs around sydney market

## Dashboards
- Production: https://tiger13tiger.github.io/DataEngineerMarketdistribution/
- Staging (dev branch preview): https://tiger13tiger.github.io/DataEngineerMarketdistribution/dev/

Both are built and deployed automatically by GitHub Actions (`.github/workflows/deploy.yml`)
from the static site in `site/`, driven by the data in `data/`. See
[CONTRIBUTING.md](CONTRIBUTING.md) for the dev → main workflow.

## Snapshots
| Date | Ads | Highlights | Report | Data |
|---|---|---|---|---|
| 2 Nov 2026 | 75 (SEEK, All Sydney) | Azure-led (33 ads), 26% contract, median $165k; ICT vacancies −15.8% YoY | [sydney-de-market-2026-11.md](snapshots/sydney-de-market-2026-11.md) | [sydney-de-market-2026-11.json](data/sydney-de-market-2026-11.json) |

Sources: SEEK live ads (keyword-matched skills/responsibilities) and the JSA Internet Vacancy Index for monthly trend proxies.

## Repo layout
- `snapshots/` — human-readable narrative report per snapshot.
- `data/` — structured metrics per snapshot (`manifest.json` lists them) that
  the dashboard reads directly.
- `site/` — the static dashboard (plain HTML/CSS/JS + Chart.js via CDN).
- `scripts/` — `validate_data.py` (schema check) and `build_site.sh` (bundles
  `site/` + `data/` + `snapshots/` into a deployable folder), both run by CI
  and by the deploy workflow.
