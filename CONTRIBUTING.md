# Contributing

This repo runs two environments off two branches:

- `dev` — staging. Every PR lands here first. GitHub Actions deploys this
  branch's dashboard to `https://tiger13tiger.github.io/DataEngineerMarketdistribution/dev/`.
- `main` — production. Only updated via PR from `dev`. GitHub Actions deploys
  this branch's dashboard to `https://tiger13tiger.github.io/DataEngineerMarketdistribution/`.

## Workflow

1. Branch from `dev` (e.g. `snapshot/2026-12`).
2. Add or update a snapshot:
   - Write the narrative in `snapshots/<id>.md`.
   - Add the matching structured data in `data/<id>.json` (see any existing
     file for the schema) and list it in `data/manifest.json`.
3. Open a PR into `dev`. The `CI` workflow validates `data/*.json` against the
   manifest and does a dry-run site build — both must pass before merging.
4. On merge to `dev`, the dashboard at `.../dev/` updates automatically.
   Check it before promoting.
5. Open a PR from `dev` into `main` to promote to production. Same CI gate
   applies. On merge, the production dashboard updates automatically.

No one pushes directly to `dev` or `main` — everything goes through a PR so
CI always runs first.

## One-time manual setup (not available via the API used to scaffold this repo)

- **GitHub Pages**: Settings → Pages → Source = "Deploy from a branch",
  branch = `gh-pages`, folder = `/ (root)`. The `Deploy dashboard` workflow
  creates and pushes to `gh-pages` on its first run.
- **Branch protection on `main`**: Settings → Branches → add a rule for
  `main` requiring a pull request before merging and requiring the `CI /
  validate` check to pass. Recommended to also apply to `dev`.
