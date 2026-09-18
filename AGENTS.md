# LaunchDesk agent instructions

## Repository operating rules

This repository is independently operable. Protect production stability, keep
changes scoped, verify work with repo-local checks, and record durable
follow-up in this repository's GitHub Issues.

## Project

- **Product**: Public launch-destination workspace — a provenance-bearing
  catalog of 966 submission destinations plus per-product queue/status/notes
  tracking.
- **Stack**: vanilla HTML/CSS/JS in `web/` (no build step), Python
  standard-library server (`server.py`) + SQLite for the local mode, catalog
  seed compiled into `web/seed.js` by `tools/build_catalog.py`.
- **Production**: vendored static bundle inside the SaaS Maker site at
  `https://sassmaker.com/launchdesk/` (Cloudflare Pages project
  `saas-maker-home`). There is no LaunchDesk Worker; the earlier standalone
  domain was retired on 2026-09-18 (issue #2).

## Commands

```bash
pnpm test                 # python3 -m unittest discover -s tests -v
pnpm run build:catalog    # regenerate seed/CSVs/single-file HTML from data/sources
pnpm run sync:showcase    # copy web/ into ../saas-maker/apps/showcase/public/launchdesk/
python3 server.py         # local SQLite mode (full features incl. link checker)
```

## Release flow

1. Edit `web/` here; run `pnpm test` and `node --check web/app.js`.
2. Run `pnpm run sync:showcase` (requires the `saas-maker` sibling checkout) to
   refresh `apps/showcase/public/launchdesk/` — the vendored snapshot is
   committed in saas-maker.
3. Commit here, then commit + deploy from `saas-maker/apps/showcase`
   (`pnpm run deploy`). Site headers, redirects and nav live in the saas-maker
   repo, not here.
4. `web/index.html` declares `https://sassmaker.com/launchdesk/` as canonical —
   the Pages middleware's soft-404 guard requires it. Keep it in sync with the
   real mount path if the app ever moves again.

## Architecture boundary

- The app selects its backend at runtime: `127.0.0.1`/`localhost` → Python API
  (`/api/workspace`, `/api/verify`); any other hostname → browser
  `localStorage`. **In production there is no API** — the deployed site is
  browser-storage mode, same as the standalone `LaunchDesk.html` build.
- `/api/verify` (live backlink check, `safeweb.py`) is intentionally not ported
  to Cloudflare (owner decision, issue #1). The button renders disabled
  off-localhost.
- There is no server-side workspace state in production. Do not add D1/KV
  persistence or accounts without a new owner decision — the README's
  single-user security boundary still applies to the Python server.
- `tools/build_catalog.py` regenerates `web/seed.js`, the CSVs, and the
  single-file `LaunchDesk.html` (gitignored build artifact) from
  `data/sources/`. `web/index.html`, `web/app.js`, `web/styles.css` are source.

## Local preview caveat

Any static server on localhost triggers the app's *server* detection branch
(`/api/workspace` fails → error page). Preview browser-mode locally on a
non-localhost hostname that resolves to 127.0.0.1, e.g.
`http://app.localhost:8000/` after `python3 -m http.server 8000 -d web`.

## Work tracking

- GitHub Issues are the operational work queue:
  https://github.com/Significant-Hobbies/launchdesk/issues
- Keep `PROJECT_STATUS.md` limited to current and shipped product truth.
- Catalog data has its own licensing (`data/sources/README.md`, `licenses/`).
  Preserve attribution and the unknown-vs-zero DR semantics described in the
  README.
