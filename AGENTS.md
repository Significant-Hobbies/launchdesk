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
- **Production**: Cloudflare Worker, static-assets only
  (`wrangler.jsonc`), at `https://launchdesk.significanthobbies.com`.

## Commands

```bash
pnpm install              # wrangler dev dependency only
pnpm run dev              # wrangler dev — see localhost note below
pnpm run deploy           # wrangler deploy --tag <git sha>
pnpm test                 # python3 -m unittest discover -s tests -v
pnpm run build:catalog    # regenerate seed/CSVs/single-file HTML from data/sources
python3 server.py         # local SQLite mode (full features incl. link checker)
```

## Architecture boundary

- The app selects its backend at runtime: `127.0.0.1`/`localhost` → Python API
  (`/api/workspace`, `/api/verify`); any other hostname → browser
  `localStorage`. **On Cloudflare there is no API** — the deployed site is
  browser-storage mode, same as the standalone `LaunchDesk.html` build.
- `/api/verify` (live backlink check, `safeweb.py`) is intentionally not ported
  to the Worker (owner decision, tracking issue #1). The button renders
  disabled off-localhost.
- There is no server-side workspace state in production. Do not add D1/KV
  persistence or accounts without a new owner decision — the README's
  single-user security boundary still applies to the Python server.
- `web/` is served verbatim by both `server.py` and the Worker. `web/_headers`
  is consumed by Cloudflare only; the Python server ignores it (not in its
  static allowlist).
- `tools/build_catalog.py` regenerates `web/seed.js`, the CSVs, and the
  single-file `LaunchDesk.html` (gitignored build artifact) from
  `data/sources/`. `web/index.html`, `web/app.js`, `web/styles.css` are source.

## Local preview caveat

`pnpm run dev` binds localhost, which triggers the app's *server* detection
branch and fails (no `/api/workspace`). Preview browser-mode locally by opening
a non-localhost hostname that resolves to 127.0.0.1, e.g.
`http://app.localhost:8788/` after `pnpm run dev`.

## Work tracking

- GitHub Issues are the operational work queue:
  https://github.com/Significant-Hobbies/launchdesk/issues
- Keep `PROJECT_STATUS.md` limited to current and shipped product truth.
- Catalog data has its own licensing (`data/sources/README.md`, `licenses/`).
  Preserve attribution and the unknown-vs-zero DR semantics described in the
  README.
