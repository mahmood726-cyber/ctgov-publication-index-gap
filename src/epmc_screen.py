"""Fail-closed classification of saved Europe PMC search responses.

A search hit, even with an exact NCT ID, is only a candidate for human review;
it is not evidence that a published paper reports the registered trial's results.
"""
from __future__ import annotations
import re

NCT_ID = re.compile(r'^NCT[0-9]{8}$')
TOKEN = re.compile(r'(?<![A-Za-z0-9])NCT[0-9]{8}(?![A-Za-z0-9])', re.I)


def nct_in_metadata(record: dict, nct: str) -> bool:
    fields = (record.get('title'), record.get('abstractText'))
    content = ' '.join(s for s in fields if isinstance(s, str))
    return nct in {x.upper() for x in TOKEN.findall(content)}


def stable_ids(hit: dict) -> set[tuple]:
    keys = set()
    for field in ('pmid', 'pmcid', 'doi'):
        value = hit.get(field)
        if isinstance(value, str) and value.strip():
            normalized = value.strip().lower()
            if field == 'doi':
                normalized = re.sub(r'^https?://(?:dx\.)?doi\.org/', '', normalized)
            keys.add((field, normalized))
    if not keys:
        source, uid = hit.get('source'), hit.get('id')
        if not source or not uid:
            raise ValueError('Search hit without stable bibliographic identifier')
        keys.add(('source_id', str(source).upper(), str(uid)))
    return keys


def deduplicate(hits: list[dict]) -> list[list[dict]]:
    """Transitive deduplication on shared identifiers, never title similarity."""
    groups: list[tuple[set, list]] = []
    for hit in hits:
        keys = stable_ids(hit)
        overlap = [i for i, (existing, _) in enumerate(groups) if keys & existing]
        if not overlap:
            groups.append((keys, [hit]))
            continue
        base = overlap[0]
        groups[base][0].update(keys)
        groups[base][1].append(hit)
        for i in reversed(overlap[1:]):
            groups[base][0].update(groups[i][0])
            groups[base][1].extend(groups[i][1])
            del groups[i]
    return [records for _, records in groups]


def classify(nct: str, payload: dict | None) -> dict:
    if not NCT_ID.fullmatch(nct):
        raise ValueError(f'Invalid NCT ID: {nct!r}')
    out = {
        'nctId': nct,
        'archived_query_status': 'NOT_VERIFIABLE',
        'query_status': 'QUERY_NOT_EXECUTED' if payload is None else 'INVALID_RESPONSE',
        'raw_hit_count': None, 'candidate_count': None,
        'metadata_identifier_candidate_count': None,
        'med_indexed_candidate_count': None, 'nonmed_only_candidate_count': None,
        'candidates': [],
        'trial_results_paper_status': 'NOT_ADJUDICATED',
        'external_publication_status': 'NOT_ESTABLISHED',
        'publication_only_visibility': 'NOT_ESTABLISHED',
    }
    if not isinstance(payload, dict):
        return out
    # Where the actual API request metadata is supplied, disallow substitution
    # of responses for another trial or a broader/different search. Missing
    # request metadata is recorded as unverified rather than presumed valid.
    if 'request' in payload:
        request = payload['request']
        query = request.get('queryString') if isinstance(request, dict) else None
        if not isinstance(query, str):
            out['archived_query_status'] = 'INVALID_REQUEST_METADATA'
            return out
        if query.strip().upper() not in {nct, f'"{nct}"'}:
            out['archived_query_status'] = 'MISMATCH'
            out['query_status'] = 'QUERY_MISMATCH'
            return out
        out['archived_query_status'] = 'EXACT_NCT_QUERY_IN_RESPONSE'
    container = payload.get('resultList')
    hits = container.get('result') if isinstance(container, dict) else None
    count = payload.get('hitCount')
    if type(count) is not int or count < 0 or not isinstance(hits, list):
        return out
    out['raw_hit_count'] = count
    if len(hits) != count or any(not isinstance(h, dict) for h in hits):
        out['query_status'] = 'INCOMPLETE_RESPONSE'
        return out
    try:
        groups = deduplicate(hits)
    except ValueError:
        return out
    out['query_status'] = 'COMPLETE_SEARCH_RESPONSE'
    out['candidate_count'] = len(groups)
    out['metadata_identifier_candidate_count'] = sum(
        any(nct_in_metadata(h, nct) for h in g) for g in groups)
    out['med_indexed_candidate_count'] = sum(
        any(str(h.get('source', '')).upper() == 'MED' for h in g) for g in groups)
    out['nonmed_only_candidate_count'] = sum(
        all(str(h.get('source', '')).upper() != 'MED' for h in g) for g in groups)
    out['candidates'] = [
        {
            'bibliographic_records': [{'source': h.get('source'), 'id': h.get('id')} for h in g],
            'pmids': sorted({str(h['pmid']) for h in g if h.get('pmid')}),
            'pmcids': sorted({str(h['pmcid']) for h in g if h.get('pmcid')}),
            'dois': sorted({str(h['doi']) for h in g if h.get('doi')}),
            'exact_nct_in_title_or_abstract': any(nct_in_metadata(h, nct) for h in g),
            'med_indexed': any(str(h.get('source', '')).upper() == 'MED' for h in g),
            'trial_results_paper': 'NOT_ADJUDICATED',
        }
        for g in groups
    ]
    return out
