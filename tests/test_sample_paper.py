"""Sanity checks for the sample paper and the shared fixtures."""
from __future__ import annotations

import ploma_config
from _findings import FAIL


def test_sample_paper_layout(sample_paper):
    for p in ("main.tex", "sections/intro.tex", "refs.bib", "Makefile", "figures/fig1.pdf",
              "review/review1.md", "results/metrics.json", "ploma.yaml"):
        assert (sample_paper / p).exists(), p


def test_sample_paper_config_validates(sample_paper):
    cfg = ploma_config.load(sample_paper)
    assert [f for f in ploma_config.validate(cfg, sample_paper) if f.status == FAIL] == []


def test_log_fixtures_present(repo_root):
    names = {p.stem for p in (repo_root / "tests/fixtures/logs").glob("*.log")}
    assert {"clean", "overfull", "undefined", "error", "rerun", "crlf_wrapped"} <= names
