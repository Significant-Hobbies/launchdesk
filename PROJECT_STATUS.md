# LaunchDesk — project status

**Live**: https://sassmaker.com/launchdesk/ (vendored bundle in Cloudflare Pages project `saas-maker-home`)
**Repo**: https://github.com/Significant-Hobbies/launchdesk

## What it is

Public launch-destination workspace. A deduplicated, source-attributed catalog
of 966 active submission prospects (1,004 records incl. 38 quarantined) with
per-product queues, statuses, notes, follow-up dates, and CSV/JSON
import/export. All visitor state lives in browser `localStorage`; the hosted
site has no backend. The Python `server.py` + SQLite mode remains for local
use and is the only mode with the live link-checker (`/api/verify`).

## Features (shipped)

- Directory: search, category/price/DR/link filters, fit/name/DR/follow-up
  sorting, pagination, bulk queue/status actions, CSV export of the view.
- Per-product workspaces: products & briefs, separate queues and submission
  records per product, notes, follow-up dates, live-listing URL field.
- Data quality view: reported-vs-verified DR, competing source claims,
  quarantined records, source history per destination.
- Import/restore: CSV/JSON catalog import, DR-only enrichment, full workspace
  JSON backup/restore, formula-escaped CSV exports.
- Provenance: source URLs, retrieval vs measurement dates, explicit unknowns
  (blank DR, never zero), source attribution in `data/sources/README.md`.
- Local mode extras (Python server only): atomic SQLite revisions with
  conflict rejection, live listing checker with SSRF/robots/redirect guards.

## Not shipped (deliberate)

- `/api/verify` on Cloudflare — skipped per owner decision (issue #1).
- Accounts, cloud workspace sync, shared catalog edits.
- Automated submission, outreach, reminders, background crawls — out of the
  product's operating rule.

## Snapshot

Catalog snapshot **2026-09-18**: 966 active / 38 quarantined, 737 with
reported DR, 633 with reported link type, 316 submission routes. Reported
metrics are source-reported, not fresh measurements. Regenerate with
`pnpm run build:catalog`.

## Timeline

- 2026-09-18 — Imported local package; briefly live on a standalone
  Worker, then moved under the SaaS Maker site per owner decision
  (issues #1–#2).
