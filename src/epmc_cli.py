"""Offline replay for raw, archived Europe PMC JSON responses.

Provide a frozen input NCT list and one JSON file per NCT. Offline by design.
A dated original 2026 cohort and original weighting are not reproduced here.
"""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
try:
    from .epmc_screen import classify, NCT_ID
except ImportError:
    from epmc_screen import classify, NCT_ID


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for piece in iter(lambda: f.read(1024 * 1024), b''):
            h.update(piece)
    return h.hexdigest()


def read_ids(path: Path) -> list[str]:
    ids: list[str] = []
    seen: set[str] = set()
    for line_number, line in enumerate(path.read_text(encoding='utf-8-sig').splitlines(), 1):
        value = line.strip()
        if not value:
            continue
        if not NCT_ID.fullmatch(value):
            raise ValueError(f'Invalid NCT ID on line {line_number}')
        if value in seen:
            raise ValueError(f'Duplicate NCT ID on line {line_number}')
        seen.add(value)
        ids.append(value)
    if not ids:
        raise ValueError('Empty cohort')
    return ids


def replay(ids_file: Path, cached: Path, output: Path) -> dict:
    ids = read_ids(ids_file)
    if output.resolve() == ids_file.resolve():
        raise ValueError('Refusing to overwrite source cohort')
    rows: list[dict] = []
    sources: dict[str, str] = {}
    for nct in ids:
        path = cached / f'{nct}.json'
        raw = None
        if path.exists():
            sources[nct] = digest(path)
            try:
                raw = json.loads(path.read_text(encoding='utf-8'))
            except (ValueError, UnicodeError):
                raw = {}
        row = classify(nct, raw)
        row['query'] = f'"{nct}"'
        row['source_response_sha256'] = sources.get(nct)
        rows.append(row)
    output.parent.mkdir(parents=True, exist_ok=True)
    partial = output.with_name(output.name + '.partial')
    try:
        partial.write_text(''.join(json.dumps(row, sort_keys=True) + '\n' for row in rows), encoding='utf-8')
        partial.replace(output)
    finally:
        partial.unlink(missing_ok=True)
    manifest = {
        'utc_replay_time': datetime.now(timezone.utc).isoformat(),
        'source_nct_list_sha256': digest(ids_file),
        'source_api_response_sha256': sources,
        'output_sha256': digest(output),
        'nct_count': len(ids),
        'query_status_counts': dict(Counter(r['query_status'] for r in rows)),
        'historical_2026_03_29_estimates_reproduced': False,
        'publication_status_adjudicated': False,
        'limitations': [
            'An NCT identifier in full text, title or abstract may refer to a protocol, systematic review or citation, not results reporting.',
            'MED denotes an index source and is not proof of publication of trial results.',
            'Unavailable, malformed and paginated incomplete results are never treated as zero hits.',
            'This tool does not establish the claimed weighted 40.8% paper rescue without original NCT sample and survey weights.',
        ],
    }
    meta_path = Path(str(output) + '.manifest.json')
    meta_path.write_text(json.dumps(manifest, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    return manifest


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--ncts', type=Path, required=True)
    ap.add_argument('--cached', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    result = replay(args.ncts, args.cached, args.output)
    print(json.dumps({'nct_count': result['nct_count'], 'statuses': result['query_status_counts']}))
    return 0 if result['query_status_counts'] == {'COMPLETE_SEARCH_RESPONSE': result['nct_count']} else 2


if __name__ == '__main__':
    raise SystemExit(main())
