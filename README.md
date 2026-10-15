# ClinicalTrials.gov Publication Index Gap

## Scientific-validity notice — 15 October 2026

The historical dashboard reports a 1,050-study sponsor-class-stratified sample drawn from 140,363 older ClinicalTrials.gov records without linked publications and weighted figures of **1.2% PubMed**, **+39.6 percentage points Europe PMC**, **40.8% any exact-ID match** and **29.1% publication-only visibility**. These are **historically reported, not independently reproduced or scientifically adjudicated estimates**. This repository does not contain the original sampled NCT IDs, frozen source snapshot, archived individual database responses, duplicate handling, manual paper-type adjudications, complete survey weights/stratum population totals or original analysis code.

A Europe PMC search result containing an NCT ID is a **candidate reference**, not proof of a publication that reports that trial's outcomes. The same article can appear in MED, PMC and other Europe PMC sources. MED/non-MED indicate index sources, not evidence quality or article relevance. Full-text NCT mentions may be incidental or refer to protocols, reviews or other studies. Missing CT.gov publication links cannot establish that no external results paper exists. Do **not** use these unverified historical figures as confirmed publication-coverage estimates, clinical findings or statutory reporting/compliance determinations.

## Reproducible independent *candidate-screen* utility

The research-only Python modules in `src/` accept one archived raw Europe PMC **JSON search response per NCT**. They deliberately do **not** recreate the historical weighted results. They export per-NCT records, distinct bibliographic candidate counts (PMID/PMCID/DOI transitive deduplication), exact title/abstract NCT token matches, and SHA-256 provenance. Missing/malformed/incomplete search responses are not scored as zero. Results-paper identity, whether an article actually reports outcomes, and external-publication status remain **NOT_ADJUDICATED / NOT_ESTABLISHED**.

```bash
python -m pip install pytest
python -m pytest -q tests
python -m src.epmc_cli --ncts sample_ncts.txt --cached epmc_raw --output epmc_candidates.jsonl
```

`sample_ncts.txt` must contain one unique NCT######## identifier per line. `epmc_raw/NCT########.json` must contain the **complete archived JSON response for that identifier**. The output is `epmc_candidates.jsonl` plus `epmc_candidates.jsonl.manifest.json` containing hashes and query-status denominators. The CLI exits nonzero if any response is unavailable, malformed or incomplete.

For independent collection, use the [Europe PMC REST search API](https://europepmc.org/RestfulWebService) with a quoted exact NCT term, `format=json`, `resultType=core`, `synonym=false` and pagination until all `hitCount` results have been retrieved. Preserve exact URLs, UTC timestamps, HTTP status, result pages and raw response bytes. This tool does not fetch, timestamp or verify requests for you; an apparent quote query in output is only the **intended** query, not proof the archive was obtained using it. Multiple-page responses must be combined carefully with source-level provenance.

A complete response with zero matches means **no hits under that specific saved query**, not proof of no publications. True publication ascertainment requires human full-text examination and comparison to trial identifiers, outcomes, protocols and publication dates.

To reproduce the historical weighted comparison, recover the original cohort and dates, sampling scheme, strata and finite-population totals, source-response archives, match adjudications, weight calculations and uncertainty estimates. Keep that reconstruction separate from this candidate-screen code.
