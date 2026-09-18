# LaunchDesk

A local-first workspace for finding submission destinations, managing launches across products, and checking the links you actually receive. Original application code; no paid LaunchRepo content is bundled.

**Hosted version**: https://sassmaker.com/launchdesk/ runs the browser-storage mode below — no account, no server state, no live backlink checking. The hosted copy is a vendored bundle inside the SaaS Maker site; refresh it with `pnpm run sync:showcase` and deploy from `saas-maker/apps/showcase`.

## Start here

Unzip the package, open a terminal in `LaunchDesk`, and run:

```sh
python3 server.py
```

Requires **Python 3.10 or newer**. No pip packages, Node, build service, API key, or account is required. The server opens `http://127.0.0.1:8765` and saves to `data/workspace.sqlite3`. Keep the terminal open while using it. Press Ctrl+C to stop. On Windows, `py -3 server.py` or `Run.bat` works with an installed Python launcher. `Run.command` is supplied for macOS/Linux.

For a browser-only alternative, open `LaunchDesk.html`. That file is self-contained and uses browser storage. It has the same catalog and workflow but **no live backlink fetching**. Browser storage support for local files varies; SQLite mode is the recommended persistent workspace. The two modes have separate storage. Move work between them using **Export backup → Restore backup**, not by expecting automatic synchronization.

## What is actually included

Snapshot assembled on **18 September 2026**:

| Coverage | Count |
|---|---:|
| Deduplicated, source-backed records | 1,004 |
| Active research prospects | 966 |
| Excluded suspect/non-destination records retained for audit | 38 |
| Active prospects with a reported DR value | 737 |
| Active prospects with a reported link type | 633 |
| Source-reported submission, entry, or instruction routes | 316 |
| Active prospects whose DR sources disagree or link sources disagree | 119 |
| Fresh authenticated DR measurements included | 0 |
| Independently verified seeded backlinks | 0 |

**This is not a completed list of 1,000 working submission forms with verified DR and link attributes.** It is an implemented workflow tool plus a provenance-bearing research catalog. The remaining work is qualifying routes, excluding unsuitable prospects, refreshing genuine DR values, and checking actual published listings. “Active” means not quarantined in this app; it does not mean the website was live-tested.

The base public CSV describes its scores as “Ahrefs-style.” Its provider provenance is unconfirmed. Other source lists report DR without a measurement date. These remain **reported values**, not fresh measurements. Unknown DR is blank/null, never zero. A real DR of zero remains zero. DA is not converted to DR.

Routes include direct forms, login flows, official instructions, community posting routes, and marketplace onboarding. Those are deliberately not all labeled submission-ready. Press and newsletter prospects usually require an editorial pitch; communities have rules; local-business sites may not fit an online-only product. A directory's reported “follow” label is not evidence about your eventual listing.

## Workflow

1. Open **Products & briefs** and enter the real URL and approved facts for your product. CodeVetter, PostTrainLLM, and Storage Daddy are placeholders with empty URLs and descriptions, not fabricated product copy.
2. Open **Submission routes** and filter for category, reported DR, link type, and price. Inspect each destination's source history and eligibility. Queue suitable destinations; submit on the destination site yourself.
3. Record submitted/live/rejected status, notes, a follow-up date, and the published listing URL. Use **Check saved listing** in SQLite mode to inspect the actual backlink. Export backups regularly.

There is no automated submission, CAPTCHA handling, email outreach, payment, account creation, scheduled reminder, or background crawl. Opening a link or copying a brief does not submit anything.

## Features

- Search, category/price/DR/link filters, fit/name/DR/follow-up ordering, pagination, and bulk queue/status actions.
- Shared destination catalog; separate product queues, statuses, notes, follow-up dates, live listing URLs, and check evidence.
- Source URLs, retrieval dates, measurement dates, competing claims, and quarantine flags. Unknown facts stay explicit.
- Add/edit destinations and products. CSV/JSON import, DR-only enrichment, filtered CSV export, full workspace backup/restore.
- Hostname deduplication, with distinct Reddit communities and GitHub repositories preserved. Imported duplicates keep destination IDs and product status history.
- SQLite atomic revision saves, conflict rejection, audit hashes, and a previous-state recovery file. Stale tabs cannot silently replace a newer revision.
- Exact-listing static-HTML checks for follow/nofollow/ugc/sponsored/mixed links, page-level robots directives, and target-domain matching.

Fit ordering is an editable-code workflow heuristic, not an SEO score or a traffic estimate. It weights a reported route and category fit more heavily than DR. Costs, approval time, traffic estimates, and automatic per-platform playbooks are not invented or promised.

## Your files

| Path | Purpose |
|---|---|
| `data/destinations.csv` | 966 active research prospects, with unknowns left blank |
| `data/all-source-records.csv` | All 1,004 records, including an explicit `quarantined` column |
| `data/excluded-source-records.csv` | 38 excluded records for review |
| `data/catalog.json` | Full seed with competing source claims |
| `data/manifest.json` | Reproducible snapshot coverage counts |
| `data/sources/` | Adapted factual source snapshots and attribution |
| `data/workspace.sqlite3` | Created on first server run; your persistent workspace |
| `data/last-good-workspace.json` | Previous state saved before the most recent successful update |
| `tests/` and `QA.md` | Tests and the exact limits of testing performed |

CSV exports are formula-escaped for safer spreadsheet opening. Full claim history and product data live in the JSON workspace backup, not the flattened CSV. Keep both the SQLite database and backups private. Stop the server before filesystem-level copying of SQLite files; in-app JSON export is the simpler portable backup. The recovery file is only the previous state, not a complete version archive.

## Import a catalog or a genuine DR export

Use **Import data** in the app, or the CLI. Accepted fields:

```csv
name,website,submission_url,dr,reported_link,category,pricing,source_url,measured_at
```

URL aliases: `url`, `website_url`, `domain`. DR aliases: `dr`, `domain_rating`, `reported_dr`. Link alias: `link_type`. Link values: `follow`, `dofollow`, `nofollow`, `ugc`, `sponsored`, `mixed`, `unknown`. Categories are the names shown in the app. Price values: `free`, `freemium`, `paid`, `unknown`.

Each imported row needs a source URL, either in the row or in the import form/CLI option. Supply the measurement date only when the underlying export actually records it. A retrieval/import timestamp does not establish when a metric was measured.

```sh
# Preview only. Does not write or initialize a database when none exists.
python3 tools/import_catalog.py dr-export.csv --source https://ahrefs.com/ --dr-only

# Commit a reviewed export; only use the actual measurement date.
python3 tools/import_catalog.py dr-export.csv --source https://ahrefs.com/ --dr-only --apply

# Add or enrich destinations, retaining existing IDs and submission history.
python3 tools/import_catalog.py destinations.csv --source https://your-source.example/ --apply
```

CLI options include `--measured-at YYYY-MM-DD` and `--db PATH`. Imports show added/updated/skipped rows. They commit valid rows when `--apply` is used, even when some other rows are skipped; exit code 2 signals skipped rows. Exit code 1 signals a failed operation. A conflicting SQLite revision rejects the commit. Reload the browser after a CLI write; do not overwrite an older tab's revision.

The importer accepts factual data you already have. It does not query Ahrefs, turn DA into DR, scrape login-protected services, or claim imported values are independently verified.

## Check one published link from the command line

```sh
python3 tools/verify_link.py https://directory.example/your-listing https://your-product.example --output check.json
```

The checker performs user-initiated public web reads from **your machine**. It checks robots permission, rate-limits requests, rejects non-public DNS answers and nonstandard ports, pins the validated IP, verifies TLS, and checks redirect destinations before fetching them. It limits redirects and response size and has socket/body timeouts. Operating-system DNS resolution is not governed by a strict end-to-end deadline.

It does not execute JavaScript, send cookies, authenticate, solve challenges, or bypass robots restrictions. A 403/challenge/network failure is **unknown**, not “dead.” A link absent from fetched HTML might be rendered by JavaScript. Redirect/tracking links whose final destination is not directly present in the fetched markup may not match. Target matching accepts the supplied domain and its subdomains; use the exact product hostname for hosted/subdomain products.

`ugc` and `sponsored` attributes are retained. Page robots/X-Robots-Tag directives are surfaced. This is link-attribute evidence, **not a Google indexing test, SEO-value estimate, or proof that Google follows a link**. Links and pages can change after a check. See the official references below.

## Local-only security boundary

The server binds only to `127.0.0.1`. Host/Origin checks, per-process CSRF tokens, static-file allowlisting, no CORS, input-size limits, and SQLite revision checks are included. The database and source files are not served as arbitrary static files. There is no telemetry, external font/icon loading, or remote database.

This is a **single-user local utility**, not an authenticated multi-user service. The local API token is CSRF protection, not user authentication. Other processes running as your user can access local data. Do not expose this server through a public tunnel or change the bind address without adding an appropriate authenticated deployment boundary. No formal security audit has been performed.

## Development and testing

```sh
python3 -m unittest discover -s tests -v
python3 tools/build_catalog.py
```

The build script regenerates seed JSON, CSVs, browser seed, and the single-file HTML from the bundled source snapshots. **It is not a live updater.** It preserves the 2026-09-18 snapshot date. Rebuilding does not overwrite an existing SQLite workspace. Use imports for enrichment or an explicit backup/restore workflow for deliberate replacement.

Runtime: Python standard library, SQLite, HTML/CSS/JavaScript. Optional UI QA uses Playwright/Chromium but those are not required to run the app. Read `QA.md` for the distinction between actual persistence/API tests and offline browser tests with a storage fixture.

## Sources, ownership, and official metric references

Source-specific licenses and adaptation notices are in `data/sources/README.md` and `licenses/`. The original app code is provided under the root MIT `LICENSE`. Source data retains its own licensing. Nothing here implies endorsement from source maintainers or LaunchRepo.

- Ahrefs DR definition: https://ahrefs.com/seo/glossary/domain-rating
- Google outbound link qualification: https://developers.google.com/search/docs/crawling-indexing/qualify-outbound-links
