# QA report — 18 September 2026

## Executed

**36 Python tests passed** with `python3 -m unittest discover -s tests -v`.

Coverage: missing/zero/invalid DR, URL normalization, destination deduplication, mismatched identity rejection, source conflicts, target-domain matching, follow/nofollow/ugc/sponsored/mixed links, page and header robots directives, deceptive-domain rejection, private/mixed DNS answers, port restrictions, robots denial, redirect permission guard, blocked-page unknown status, SQLite atomic revision and recovery behavior, product status isolation, static-file allowlisting, Host/Origin checks, CSRF token checks, stale revision rejection, CSV header/DA rejection, import row atomicity, and preservation of submission history during DR enrichment.

**Nine offline browser checks passed**, with **zero JavaScript page errors** in Chromium: initial 966-prospect render and pagination; search/queue/save acknowledgement; product queue isolation; evidence drawer/Escape close; quoted CSV/formula escaping/missing-zero-boolean DR; a zero-DR CSV import; saved-workspace reload; stale-revision unsaved warning; and a 390-pixel responsive render. Desktop and mobile screenshots were inspected.

JavaScript syntax checked with `node --check web/app.js`. Catalog rebuilt with **zero parser errors**, 1,004 unique record identities, and the coverage recorded in `data/manifest.json`.

## Test boundaries

Browser navigation was restricted in the build environment. The browser interaction checks used Playwright `set_content` with an explicit in-memory `localStorage` fixture. They are **not** evidence that file-origin persistence or browser-to-localhost navigation was exercised end to end. SQLite persistence and local HTTP API behavior were exercised independently through Python tests. The shipped app does not include the test storage fixture.

No external production destination was crawled from this environment. Network responses/DNS used in tests were mocked. The checker logic and security cases were tested, but no live-backlink, fresh Ahrefs, Google-indexing, browser compatibility across all engines, or formal penetration audit is claimed. No automated mass-submission implementation exists.

The catalog itself remains a research dataset, not 1,000 independently verified submission-ready sites. Follow-up dates are stored but do not produce background notifications.
