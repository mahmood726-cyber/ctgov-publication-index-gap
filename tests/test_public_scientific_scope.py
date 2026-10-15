"""Scientifically meaningful guards for publication-matching public claims."""
import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("path", ["index.html", "dashboard.html", "e156-submission/index.html"])
def test_historical_publication_figures_have_visible_reproducibility_warning(path):
    page = (ROOT / path).read_text(encoding="utf-8")
    assert page.count('class="validation-note"') == 1
    assert "not independently reproduced" in page.lower()
    assert "not verified publication rates" in page.lower()
    assert "statutory reporting" in page
    assert "candidate-screen tool" in page
    assert page.index('class="validation-note"') < page.index('class="body-section"') if path.startswith("e156-submission/") else page.index('class="validation-note"') < page.index('class="hero"')


@pytest.mark.parametrize("path", [
    "E156-PROTOCOL.md", "paper/manuscript.md",
    "e156-submission/paper.md", "e156-submission/protocol.md",
])
def test_provenance_limitations_in_written_publications(path):
    text = (ROOT / path).read_text(encoding="utf-8")
    assert "not independently reproduced" in text.lower()
    assert "NCT" in text
    assert "weight" in text.lower()
    assert "FULL REGISTRY RUN" not in text


@pytest.mark.parametrize("path", ["e156-submission/config.json", "e156-submission/paper.json"])
def test_e156_json_does_not_claim_scientific_reproduction(path):
    record = json.loads((ROOT / path).read_text(encoding="utf-8"))
    assert record["scientific_reproducibility"]["historical_estimates_reproduced"] is False
    assert record["scientific_reproducibility"]["publication_results_adjudicated"] is False
    assert "not independently reproduced" in record["notes"]["validation"]
