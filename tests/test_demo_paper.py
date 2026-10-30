import json, re, shutil, subprocess
import pytest
from conftest import REPO_ROOT
from _banned import EM_DASH_RE

DEMO = REPO_ROOT / "examples" / "demo-paper"

def test_config_loads_and_names_the_metrics():
    import ploma_config
    cfg = ploma_config.load(DEMO)
    assert cfg["document"]["main"] == "main.tex"
    assert cfg["pipeline"]["enabled"] is True
    assert set(cfg["pipeline"]["metric_keys"]) >= {"latency_cut_vs_otel_pct", "latency_cut_vs_rawlogs_pct", "storage_ratio", "n_frameworks"}

def test_designed_conflict_is_present():
    intro = (DEMO / "sections" / "intro.tex").read_text()
    bench = json.loads((DEMO / "results" / "bench.json").read_text())
    assert r"31\%" in intro and "27.4" not in intro
    assert bench["latency_cut_vs_otel_pct"] == 27.4
    assert bench["latency_cut_vs_rawlogs_pct"] == 41.2
    assert "OpenTelemetry" not in intro and "raw log" not in intro.lower()

def test_every_bib_entry_has_a_doi():
    bib = (DEMO / "refs.bib").read_text()
    entries = re.split(r"\n(?=@)", bib.strip())
    assert len(entries) >= 6
    for e in entries:
        assert re.search(r"^\s*doi\s*=", e, re.M), e[:60]

def test_marked_fictional_and_dash_free():
    assert "fictional" in (DEMO / "main.tex").read_text()
    for p in DEMO.rglob("*"):
        if p.suffix in {".tex", ".bib", ".json", ".yaml"}:
            assert not EM_DASH_RE.search(p.read_text()), p

@pytest.mark.skipif(shutil.which("pdflatex") is None, reason="TeX Live not installed")
def test_compiles(tmp_path):
    dst = tmp_path / "demo"; shutil.copytree(DEMO, dst)
    subprocess.run(["make"], cwd=dst, check=True, capture_output=True)
    assert (dst / "main.pdf").is_file()
