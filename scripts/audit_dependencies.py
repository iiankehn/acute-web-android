#!/usr/bin/env python3
"""Check pinned Maven catalog and registry Cargo versions against OSV advisories.

This inventory does not establish Android runtime reachability or resolve Maven transitives.
Only public dependency coordinates are sent to OSV; no app/user data or credentials.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import tomllib
import urllib.request

API = 'https://api.osv.dev/v1/'


def inventory(catalog, cargo):
    queries = []
    for item in catalog['libraries'].values():
        if 'module' not in item:
            continue
        version = item.get('version')
        if isinstance(version, dict) and 'ref' in version:
            version = catalog['versions'][version['ref']]
        if isinstance(version, str):
            queries.append(dict(package=dict(ecosystem='Maven', name=item['module']), version=version))
    for item in cargo['package']:
        if item.get('source', '').startswith('registry+'):
            queries.append(dict(package=dict(ecosystem='crates.io', name=item['name']), version=item['version']))
    if not queries or not any(q['package']['ecosystem'] == 'Maven' for q in queries) or not any(q['package']['ecosystem'] == 'crates.io' for q in queries):
        raise ValueError('Incomplete Maven/Rust inventory')
    return list({json.dumps(q, sort_keys=True): q for q in queries}.values())


def request(path, payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(API + path, data=data, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=45) as response:
        content = response.read(8 * 1024 * 1024 + 1)
        if len(content) > 8 * 1024 * 1024:
            raise ValueError('OSV response exceeded size bound')
        return json.loads(content)


def scan(queries, fetch=request):
    rows = []
    for start in range(0, len(queries), 100):
        batch = queries[start:start + 100]
        pending = [(i, dict(q)) for i, q in enumerate(batch)]
        advisory_ids = [set() for _ in batch]
        seen_tokens = [set() for _ in batch]
        for _ in range(50):
            response = fetch('querybatch', {'queries': [q for _, q in pending]})
            results = response.get('results')
            if not isinstance(results, list) or len(results) != len(pending):
                raise ValueError('Incomplete OSV response')
            next_page = []
            for (index, query), result in zip(pending, results):
                if not isinstance(result, dict):
                    raise ValueError('Malformed OSV result')
                for advisory in result.get('vulns', []):
                    if not isinstance(advisory.get('id'), str):
                        raise ValueError('Missing advisory ID')
                    advisory_ids[index].add(advisory['id'])
                token = result.get('next_page_token')
                if token:
                    if not isinstance(token, str) or token in seen_tokens[index]:
                        raise ValueError('Invalid OSV pagination')
                    seen_tokens[index].add(token)
                    next_page.append((index, dict(query, page_token=token)))
            pending = next_page
            if not pending:
                break
        else:
            raise ValueError('OSV pagination limit exceeded')
        rows.extend(dict(query=q, advisory_ids=sorted(ids)) for q, ids in zip(batch, advisory_ids))
    details = {}
    for row in rows:
        for advisory_id in row['advisory_ids']:
            if advisory_id not in details:
                record = fetch('vulns/' + advisory_id)
                if record.get('id') != advisory_id or not record.get('affected'):
                    raise ValueError('Incomplete advisory record')
                details[advisory_id] = record
    return rows, details


def is_informational(record):
    affected = record.get('affected', [])
    return bool(affected) and all(a.get('database_specific', {}).get('informational') for a in affected)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog', required=True, type=Path)
    parser.add_argument('--cargo', required=True, type=Path)
    parser.add_argument('--report', required=True, type=Path)
    args = parser.parse_args()
    try:
        queries = inventory(tomllib.loads(args.catalog.read_text()), tomllib.loads(args.cargo.read_text()))
        rows, details = scan(queries)
        blockers = sorted(key for key, value in details.items() if not is_informational(value))
        report = dict(checked_at=datetime.now(timezone.utc).isoformat(), scope=__doc__, packages=rows,
                      advisories=details, unresolved_vulnerability_ids=blockers)
        args.report.write_text(json.dumps(report, indent=2) + '\n')
        print(f'Checked {len(rows)} dependency versions; {len(details)} advisory records; {len(blockers)} unresolved vulnerabilities')
        for key, value in details.items():
            print(key, 'maintenance' if is_informational(value) else 'vulnerability', value.get('summary', ''))
    except Exception as error:
        parser.exit(2, f'Dependency audit incomplete: {error}\n')
    return 1 if blockers else 0

if __name__ == '__main__':
    raise SystemExit(main())
