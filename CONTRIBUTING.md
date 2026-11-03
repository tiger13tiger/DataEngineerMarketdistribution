# Contributing

This repo runs two environments off two branches:

- `dev` — staging. Every PR lands here first. GitHub Actions deploys this
  branch's dashboard to `https://tiger13tiger.github.io/DataEngineerMarketdistribution/dev/`.
- `main` — production. Only updated via PR from `dev`. GitHub Actions deploys
  this branch's dashboard to `https://tiger13tiger.github.io/DataEngineerMarketdistribution/`.

No one pushes directly to `dev` or `main` — everything goes through a PR so
CI always runs first.

## Data pipeline (medallion)

`pipeline/` extracts and refines market data in three layers:

1. **Bronze** (`bronze/seek/<run-date>/`) — raw SEEK search API responses,
   exactly as received. `pipeline/extract_seek.py`.
2. **Staging** (`staging/<run-date>/ads.csv`) — deduplicated, parsed ads with
   derived fields (level, cloud, skills, responsibilities).
   `pipeline/transform_staging.py`.
3. **Golden** (`data/<id>.json` + `data/manifest.json`) — the aggregated
   metrics the dashboard actually reads. `pipeline/transform_golden.py`.

`.github/workflows/pipeline.yml` runs this weekly (and on manual
`workflow_dispatch`) and opens a PR into `dev` with the new bronze/staging/
golden files — it never pushes directly, so CI and a human review still gate
every data update, same as any other change.

**Caveats, read before trusting the schedule:**
- `pipeline/extract_seek.py` hits an undocumented SEEK endpoint reverse
  engineered from the website. It can change, rate-limit, or block
  GitHub-hosted runner IPs without notice. Run it manually once
  (Actions → "Market data pipeline" → "Run workflow") and check the opened
  PR's diff before relying on the schedule.
- GitHub only reads a workflow's `schedule:` trigger from the file as it
  exists on the **default branch** (`main`). The cron won't actually fire
  until this workflow file is promoted to `main`; use `workflow_dispatch` on
  `dev` in the meantime.
- Search-result teasers are short. Skills/responsibilities keyword matching
  is only computed over the subset of ads whose full detail page was fetched
  (`--detail-fetch-limit`, default 30/run) — `methodology` in each golden
  file states the sample size used.
- Salary and the JSA monthly-vacancy trend aren't computed by the automated
  pipeline yet (SEEK's search results don't carry them, and JSA is a
  separate public dataset) — those fields are `null` on automated snapshots.
  The dashboard and `scripts/validate_data.py` both treat them as optional.

## Adding or fixing a snapshot by hand

1. Branch from `dev` (e.g. `snapshot/2026-12`).
2. Write the narrative in `snapshots/<id>.md` and the matching structured
   data in `data/<id>.json` (see any existing file for the schema), then
   list it in `data/manifest.json`.
3. Open a PR into `dev`. `CI` validates `data/*.json` against the manifest
   and does a dry-run site build — both must pass before merging.
4. On merge to `dev`, the dashboard at `.../dev/` updates automatically.
5. Open a PR from `dev` into `main` to promote to production.

## One-time manual setup (not available via the API used to scaffold this repo)

- **GitHub Pages**: Settings → Pages → Source = "Deploy from a branch",
  branch = `gh-pages`, folder = `/ (root)`. Already done if the dashboards
  are live.
- **Branch protection on `main`**: Settings → Branches → add a rule for
  `main` requiring a pull request before merging and requiring the `CI /
  validate` check to pass. Recommended to also apply to `dev`.
