#!/usr/bin/env python3
"""Import a CSV/JSON catalog or DR export into the local SQLite workspace.

Defaults to a dry run. Pass --apply to commit; existing submissions survive.
No network calls are made. Source URLs document where your data came from.
"""
from __future__ import annotations
import argparse
import copy
import csv
import io
import json
import sys
from datetime import datetime, timezone, date
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from catalog import ROOT, build_record, clean_url, identity, parse_dr, CATEGORIES
from store import Store, validate_state


def load_records(path: Path) -> list[dict]:
    if path.stat().st_size > 10_000_000:
        raise ValueError('Input exceeds 10 MB')
    text = path.read_text(encoding='utf-8-sig')
    if path.suffix.lower() == '.json':
        obj = json.loads(text)
        rows = obj if isinstance(obj, list) else obj.get('destinations', obj.get('catalog'))
        if not isinstance(rows, list):
            raise ValueError('Expected a JSON array, destinations array, or catalog array')
    else:
        matrix = list(csv.reader(io.StringIO(text)))
        if len(matrix) < 2:
            raise ValueError('CSV has no data rows')
        headers = [h.strip().lower() for h in matrix[0]]
        if not all(headers) or len(headers) != len(set(headers)):
            raise ValueError('CSV headers must be nonempty and unique')
        if {'da', 'domain_authority'} & set(headers) and not {'dr', 'domain_rating', 'reported_dr'} & set(headers):
            raise ValueError('DA is not DR. Supply a genuine DR field')
        rows = []
        for i, values in enumerate(matrix[1:], 2):
            if not values:
                continue
            if len(values) != len(headers):
                rows.append({'_error': f'Column count mismatch on CSV line {i}'})
            else:
                rows.append(dict(zip(headers, values)))
    if len(rows) > 50_000:
        raise ValueError('Input limit is 50,000 rows')
    return rows


def enrich(state: dict, rows: list[dict], source: str, measured_at: str | None = None,
           dr_only: bool = False) -> tuple[dict, dict]:
    staged = copy.deepcopy(state)
    by_key = {r['key']: r for r in staged['catalog']}
    report = {'added': 0, 'updated': 0, 'skipped': 0, 'errors': []}
    stamp = datetime.now(timezone.utc).isoformat()
    for i, x in enumerate(rows, 1):
        try:
            if not isinstance(x, dict):
                raise ValueError('Row must be an object')
            if x.get('_error'):
                raise ValueError(x['_error'])
            url = clean_url(x.get('website_url') or x.get('website') or x.get('url') or x.get('domain') or '')
            if not url:
                raise ValueError('Missing destination URL/domain')
            key = identity(url)
            src = clean_url(x.get('source_url') or x.get('source') or source)
            if not src:
                raise ValueError('A source URL is required')
            dr = parse_dr(x.get('domain_rating', x.get('reported_dr', x.get('dr'))))
            measured = x.get('measured_at') or measured_at or None
            if measured:
                date.fromisoformat(measured)  # Require an explicit YYYY-MM-DD date.
            link = str(x.get('link_type') or x.get('reported_link') or 'unknown').lower()
            link = {'dofollow': 'follow', 'd': 'follow', 'n': 'nofollow'}.get(link, link)
            if link not in {'follow','nofollow','ugc','sponsored','mixed','unknown'}:
                link = 'unknown'
            submission = clean_url(x.get('submission_url') or '')
            prior = by_key.get(key)
            if dr_only and (prior is None or dr is None):
                raise ValueError('DR-only import requires a known destination and numeric DR')
            if prior and len(prior['claims']) >= 200:
                raise ValueError('Source claim history limit reached (200)')
            name = str(x.get('name') or (prior or {}).get('name') or key).strip()
            if not 1 <= len(name) <= 500:
                raise ValueError('Destination name must be 1–500 characters')
            pricing = str(x.get('pricing') or 'unknown').lower()
            candidate = build_record(url, dr, 'unknown' if dr_only else link, pricing,
                                     name, src, submission, source_id='user import')
            candidate['source_retrieved_at'] = stamp
            candidate['measured_at'] = measured
            candidate['metric_provider'] = 'User-imported DR; see source' if dr is not None else 'Not supplied'
            candidate['claims'][0].update(retrieved_at=stamp, measured_at=measured)
            if x.get('category') in CATEGORIES:
                candidate['category'] = x['category']
            if prior:
                candidate_old = copy.deepcopy(prior)
                candidate_old['claims'].append(candidate['claims'][0])
                if dr is not None:
                    for field in ('reported_dr','measured_at','source_url','source_retrieved_at','metric_provider'):
                        candidate_old[field] = candidate[field]
                if not dr_only:
                    if link != 'unknown':
                        candidate_old['reported_link'] = link
                    if submission:
                        candidate_old['submission_url'] = submission
                        candidate_old['route_status'] = 'source-reported'
                    if x.get('category') in CATEGORIES:
                        candidate_old['category'] = x['category']
                for field, flag in [('dr', 'DR sources disagree'), ('link', 'Link sources disagree')]:
                    values = {c.get(field) for c in candidate_old['claims']} - {None, 'unknown'}
                    if len(values) > 1 and flag not in candidate_old['flags']:
                        candidate_old['flags'].append(flag)
                prior.clear()
                prior.update(candidate_old)
                report['updated'] += 1
            else:
                candidate['quarantined'] = 'Suspect source data' in candidate['flags']
                staged['catalog'].append(candidate)
                by_key[key] = candidate
                report['added'] += 1
        except (ValueError, TypeError, KeyError) as exc:
            report['skipped'] += 1
            report['errors'].append({'row': i, 'error': str(exc)})
    validate_state(staged)
    return staged, report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file', type=Path)
    parser.add_argument('--source', required=True, help='Provenance URL, e.g. https://ahrefs.com/')
    parser.add_argument('--measured-at', help='Actual measurement date, YYYY-MM-DD; never guessed')
    parser.add_argument('--db', type=Path, default=ROOT/'data'/'workspace.sqlite3')
    parser.add_argument('--dr-only', action='store_true')
    parser.add_argument('--apply', action='store_true', help='Commit the import instead of previewing')
    args = parser.parse_args()
    try:
        seed = json.loads((ROOT/'data'/'catalog.json').read_text())
        if not args.db.exists() and not args.apply:
            from catalog import initial_state
            revision, state = 0, initial_state(seed)
            store = None
        else:
            store = Store(args.db, seed)
            revision, state = store.read()
        state, report = enrich(state, load_records(args.file), args.source, args.measured_at, args.dr_only)
        if args.apply:
            report['revision'] = store.write(state, revision, action='catalog-import')
        report['applied'] = args.apply
        print(json.dumps(report, indent=2))
        return 2 if report['skipped'] else 0
    except Exception as exc:
        print(f'Import failed: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
