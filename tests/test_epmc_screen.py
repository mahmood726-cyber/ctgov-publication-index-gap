import json
from pathlib import Path
import pytest
from src.epmc_screen import classify, nct_in_metadata, deduplicate
from src.epmc_cli import replay

NCT = 'NCT02993146'


def response(*records):
    return {'hitCount': len(records), 'resultList': {'result': list(records)}}


def test_missing_is_not_zero_hits():
    row = classify(NCT, None)
    assert row['query_status'] == 'QUERY_NOT_EXECUTED'
    assert row['candidate_count'] is None
    assert row['external_publication_status'] == 'NOT_ESTABLISHED'


def test_exact_empty_success_is_not_publication_adjudication():
    row = classify(NCT, response())
    assert row['query_status'] == 'COMPLETE_SEARCH_RESPONSE'
    assert row['candidate_count'] == 0
    assert row['trial_results_paper_status'] == 'NOT_ADJUDICATED'


def test_fulltext_only_hit_not_promoted_to_trial_publication():
    row = classify(NCT, response({'source': 'MED', 'id': '1', 'pmid': '1', 'title': 'Protocol systematic review', 'abstractText': 'Background'}))
    assert row['candidate_count'] == 1
    assert row['metadata_identifier_candidate_count'] == 0
    assert row['external_publication_status'] == 'NOT_ESTABLISHED'


def test_exact_token_not_substring():
    assert nct_in_metadata({'title': '(NCT02993146): trial methods'}, NCT)
    assert not nct_in_metadata({'title': 'XNCT02993146 and NCT029931460'}, NCT)


def test_transitive_dedupe_med_and_pmc():
    a = {'source': 'MED', 'id': '1', 'pmid': '1', 'doi': '10.1/demo', 'title': NCT}
    b = {'source': 'PMC', 'id': 'PMC2', 'pmcid': 'PMC2', 'doi': 'https://doi.org/10.1/demo', 'title': 'Protocol'}
    c = {'source': 'PPR', 'id': '3', 'pmcid': 'PMC2', 'title': 'Protocol'}
    groups = deduplicate([a, b, c])
    assert len(groups) == 1
    row = classify(NCT, response(a, b, c))
    assert row['candidate_count'] == 1
    assert row['med_indexed_candidate_count'] == 1
    assert row['nonmed_only_candidate_count'] == 0


def test_incomplete_api_pagination_must_not_count_as_zero():
    payload = {'hitCount': 50, 'resultList': {'result': []}}
    row = classify(NCT, payload)
    assert row['query_status'] == 'INCOMPLETE_RESPONSE'
    assert row['candidate_count'] is None


@pytest.mark.parametrize('payload', ['bad', {'resultList': {'result': []}}, {'hitCount': 0, 'resultList': {}}])
def test_malformed_rejected(payload):
    assert classify(NCT, payload)['query_status'] == 'INVALID_RESPONSE'


def test_offline_replay_manifest_and_not_executed(tmp_path):
    ids = tmp_path / 'ncts.txt'
    ids.write_text(NCT + '\nNCT00000001\n')
    cached = tmp_path / 'cached'
    cached.mkdir()
    (cached / f'{NCT}.json').write_text(json.dumps(response()))
    out = tmp_path / 'audit.jsonl'
    manifest = replay(ids, cached, out)
    assert manifest['nct_count'] == 2
    assert manifest['query_status_counts'] == {'COMPLETE_SEARCH_RESPONSE': 1, 'QUERY_NOT_EXECUTED': 1}
    assert manifest['historical_2026_03_29_estimates_reproduced'] is False
    rows = [json.loads(x) for x in out.read_text().splitlines()]
    assert rows[1]['candidate_count'] is None
    assert Path(str(out) + '.manifest.json').exists()


def test_duplicate_ids_rejected(tmp_path):
    ids = tmp_path / 'ncts.txt'
    ids.write_text(NCT + '\n' + NCT + '\n')
    with pytest.raises(ValueError, match='Duplicate'):
        replay(ids, tmp_path, tmp_path / 'out.jsonl')
