# LaunchDesk agent instructions

## Repository operating rules

LaunchDesk was absorbed into SaaS Maker by owner decision on 2026-09-20.
Do not treat it as an active standalone product or create an independent roadmap.
Retain this checkout as the dataset source and historical implementation used by
SaaS Maker's /launchdesk feature. Track any future work in SaaS Maker's GitHub
Issues. Protect production stability, keep changes scoped, and verify source
changes with repo-local checks.

## Project

- **Product**: A provenance-honest catalog of 966 launch destinations, plus a
  local-first workspace app for per-product queue/status/notes tracking.
- **Public surface**: a read-only catalog browser at
  `https://sassmaker.com/launchdesk` — a native page in the SaaS Maker site
  (Cloudflare Pages project `saas-maker-home`) rendered from
  `apps/showcase/src/data/launchdesk.json`, which is generated from this repo's
  `data/catalog.json`. The `web/` app itself is not deployed.
- **Stack**: vanilla HTML/CSS/JS in `web/` (no build step), Python
  standard-library server (`server.py`) + SQLite for the local mode, catalog
  seed compiled into `web/seed.js` by `tools/build_catalog.py`.

## Commands

```bash
pnpm test                 # python3 -m unittest discover -s tests -v
pnpm run build:catalog    # regenerate seed/CSVs/single-file HTML from data/sources
pnpm run sync:showcase    # regenerate showcase's src/data/launchdesk.json
python3 server.py         # local SQLite mode (full features incl. link checker)
```

## Release flow

- **Catalog data**: edit `data/sources/` → `pnpm run build:catalog` →
  `pnpm test` → `pnpm run sync:showcase` → commit here → commit + deploy from
  `saas-maker/apps/showcase` (`pnpm run deploy`).
- **`web/` app changes**: affect only the local app; verify with `pnpm test`
  and `node --check web/app.js`. No deploy step exists for them.
- The public page's presentation (filters, columns, styling) lives in
  `saas-maker/apps/showcase/src/pages/launchdesk.astro`, not here.

## Architecture boundary

- The app selects its backend at runtime: `127.0.0.1`/`localhost` → Python API
  (`/api/workspace`, `/api/verify`); any other hostname → browser
  `localStorage`.
- `/api/verify` (live backlink check, `safeweb.py`) is intentionally not ported
  to Cloudflare (owner decision, issue #1). The button renders disabled
  off-localhost.
- There is no server-side workspace state anywhere. Do not add persistence or
  accounts without a new owner decision — the README's single-user security
  boundary still applies to the Python server.
- `tools/build_catalog.py` regenerates `web/seed.js`, the CSVs, and the
  single-file `LaunchDesk.html` (gitignored build artifact) from
  `data/sources/`. `web/index.html`, `web/app.js`, `web/styles.css` are source.

## Local preview caveat

Any static server on localhost triggers the app's *server* detection branch
(`/api/workspace` fails → error page). Preview browser-mode locally on a
non-localhost hostname that resolves to 127.0.0.1, e.g.
`http://app.localhost:8000/` after `python3 -m http.server 8000 -d web`.

## Work tracking

- SaaS Maker owns the operational work queue:
  https://github.com/sass-maker/saas-maker/issues
- Keep `PROJECT_STATUS.md` limited to current and shipped product truth.
- Catalog data has its own licensing (`data/sources/README.md`, `licenses/`).
  Preserve attribution and the unknown-vs-zero DR semantics described in the
  README.
