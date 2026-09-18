# Source snapshots and attribution

Retrieved **2026-09-18**. These files are adapted factual extracts, not endorsements, authenticated metric measurements, or complete mirrors. Despite the `.tsv` extension, the snapshots use `|` delimiters to preserve commas in names. Format: URL | reported DR | link code | price code | name | optional entry URL | optional category | optional eligibility.

## AI BrandFactory / SaaS Directories

File: `brandfactory.tsv`.
Creator/maintainer: **AI BrandFactory**, repository **mezmer90/saas-directories**.
Source: https://github.com/mezmer90/saas-directories/blob/main/saas-directories.csv
Source CSV SHA: `e3b1420eb6e2ba9aea7a44eb441f41585fe34ece`.
License: **CC BY 4.0**, https://creativecommons.org/licenses/by/4.0/ .

Adaptations: selected factual fields, light name normalization, categorization, deduplication, exclusion of non-destinations, and suspect/truncated-path flags. Upstream has 921 rows; the bundled factual extract is selected, not an assertion that all upstream rows are usable destinations. The source calls its values **“Ahrefs-style” DR**. Metric-provider provenance and measurement dates are unconfirmed. Known typographic errors are retained as source evidence and flagged, not silently certified as real domains. No endorsement is implied.

## Submitlist / Awesome Submitlist

File: `submitlist.tsv`.
Creator: **alvinunreal / Submitlist**.
Source: https://github.com/alvinunreal/awesome-submitlist
Structured data: https://github.com/alvinunreal/awesome-submitlist/blob/main/data/destinations.json
README SHA: `c306ee7c50ede496a6e8d6f318182cc303a6ce07`.
Structured-data SHA: `f08b2e736170d5472e6ea20851e2197e2ce2ee4f`.
License: **CC0 1.0**, https://creativecommons.org/publicdomain/zero/1.0/ .

Selected factual URL, DR, link-type, price, and entry-route extracts; descriptive text is adapted. Source-reported snapshot date 2026-09-14 is kept separate from retrieval and metric measurement dates. No metric measurement date was established. External onboarding URLs are associated with the actual destination, not misinterpreted as the rating domain. Community permission notes are source-reported; check current moderator rules. A promotion-thread-only or comments-only note is not permission to create a standalone promotional post.

## LaunchDB / Awesome SaaS Directories

File: `launchdb.tsv`.
Creator: **Shubham Bhamare / theshubh77**.
Source: https://github.com/theshubh77/awesome-saas-directories/blob/master/README.md
README SHA: `726680dcb81f1c1c9e868d16b97fbb93d2183ebe`.
License: **CC0 / rights waiver stated by the creator**. Reference: https://creativecommons.org/publicdomain/zero/1.0/ .

Selected URL, name, DR, and submission-route facts from the 180-entry list. The source credits Ahrefs for DR; those remain source-reported values with no established measurement date. This source does not provide a structured link-type field: missing link values are not inferred from promotional copy. Attribution/marketing query parameters were removed where they were nonfunctional. Community/repository destinations preserve their identity rather than collapsing into one generic Reddit/GitHub entry. Generic homepage links remain research prospects unless a concrete entry route is recorded.

## Best Of AI / AI Directories

File: `ai-directories.tsv`.
Creator: **Best Of AI**.
Source: https://github.com/best-of-ai/ai-directories/blob/main/README.md
README SHA: `cf8e3e1e33a5275784f7020fe1f8131abca0b98d`.
License: **MIT, Copyright (c) 2024 Best Of AI**. Full required notice: `../../licenses/Best-Of-AI-MIT.txt`.

Selected factual names and URLs, normalized and merged into the catalog. This source does not supply structured DR, price, or link-type measurements. Incidental marketing claims in descriptions are not imported as verified metrics. Categories are editorial adaptations.

## Combining the sources

All compiled records retain claim-level source URLs, source IDs, dates, and conflicting values. Retrieval date is **not** metric measurement date. Unknowns stay null/unknown. Reported prices, rules, routes, and link types may have changed. Inclusion in a public list is not evidence that a website is alive, accepting submissions, suitable for your product, or valuable for SEO.

The compiled catalog and CSVs retain the relevant source data's license obligations; the app's MIT license does not replace those source licenses. No paid LaunchRepo database or private playbook has been copied. Sources are not endorsing this app or its adapted classifications.
