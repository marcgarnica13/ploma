"""validate_bib.py: structural and semantic bibliography audit, report, gate and state entries.

Every semantic test injects ``fetch``; nothing touches the network."""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import pytest

import gate
import state
import validate_bib
from bib_check import parse_bib

SAMPLE_HEADINGS = ["## Summary", "## Structural", "## Citation drift", "## DOI verification",
                   "## Style consistency", "## Next steps"]


def _plain(s: str) -> str:
    return re.sub(r"[{}]", "", s)


def _item(entry) -> dict:
    authors = []
    for a in entry.fields.get("author", "").split(" and "):
        a = _plain(a.strip())
        family, _, given = a.partition(",")
        authors.append({"family": family.strip(), "given": given.strip()})
    return {"DOI": entry.fields.get("doi", ""), "title": [_plain(entry.fields.get("title", ""))],
            "author": authors, "issued": {"date-parts": [[int(entry.fields["year"])]]}}


def verifying_fetch(bib: Path, calls: list | None = None):
    """Crossref answers every DOI and title query with the entry itself; other sources are empty."""
    entries = parse_bib(bib.read_text(encoding="utf-8"))
    by_doi = {e.fields["doi"].lower(): e for e in entries if e.fields.get("doi")}

    def fetch(url: str, headers: dict) -> tuple[int, str]:
        if calls is not None:
            calls.append(url)
        u = urlparse(url)
        if u.netloc == "api.crossref.org" and u.path.startswith("/works/"):
            e = by_doi.get(unquote(u.path[len("/works/"):]).lower())
            return (200, json.dumps({"message": _item(e)})) if e else (404, "")
        if u.netloc == "api.crossref.org":
            return 200, json.dumps({"message": {"items": [_item(e) for e in entries]}})
        if u.netloc == "api.openalex.org":
            return 200, json.dumps({"results": []})
        return 200, json.dumps({"data": []})
    return fetch


def unreachable_fetch(url: str, headers: dict) -> tuple[int, str]:
    return 0, ""


def missing_fetch(url: str, headers: dict) -> tuple[int, str]:
    if "api.crossref.org/works/" in url:
        return 404, ""
    if "crossref" in url:
        return 200, json.dumps({"message": {"items": []}})
    if "openalex" in url:
        return 200, json.dumps({"results": []})
    return 200, json.dumps({"data": []})


@pytest.fixture
def cache(tmp_path) -> Path:
    return tmp_path / "cache" / "cite_lookup.json"


def _ids(rep) -> dict:
    return {f.id: f.status for f in rep.findings}


def test_structural_pass_on_sample(sample_paper, cfg):
    rep = validate_bib.run(sample_paper, cfg, semantic=False)
    assert rep.verdict == "PASS"
    assert rep.lookups == []
    assert rep.report_path == sample_paper.resolve() / "quality_reports" / "bib_audit_structural.md"
    text = rep.report_path.read_text(encoding="utf-8")
    assert "**Verdict: PASS.**" in text
    assert "FernandezNavarro2016" in text  # unused entry, informational
    entry = gate.load(sample_paper, cfg)["checks"]["bib"]
    assert entry["status"] == "PASS" and entry["artifact"] == "quality_reports/bib_audit_structural.md"
    last = state.load(sample_paper, cfg)["events"][-1]
    assert last["skill"] == "validate-bib" and last["status"] == "PASS"


def test_missing_key_fails_and_structural_section_names_it(sample_paper, cfg):
    intro = sample_paper / "sections" / "intro.tex"
    intro.write_text(intro.read_text(encoding="utf-8").replace("\\cite{Elo1978}", "\\cite{Elo1987}"),
                     encoding="utf-8")
    rep = validate_bib.run(sample_paper, cfg, semantic=False)
    assert rep.verdict == "FAIL"
    assert _ids(rep)["bib.missing.Elo1987"] == "FAIL"
    text = rep.report_path.read_text(encoding="utf-8")
    assert "**Verdict: FAIL.**" in text
    structural = text.split("## Structural", 1)[1].split("\n## ", 1)[0]
    assert "Elo1987" in structural and "intro.tex:5" in structural
    assert gate.load(sample_paper, cfg)["checks"]["bib"]["status"] == "FAIL"


def test_semantic_all_verified_passes_with_doi_table(sample_paper, cfg, cache):
    calls: list = []
    rep = validate_bib.run(sample_paper, cfg, semantic=True, fetch=verifying_fetch(sample_paper / "refs.bib", calls),
                           cache_path=cache, delay_s=0)
    assert rep.verdict == "PASS"
    assert {r.key: r.status for r in rep.lookups} == {"Bradley1952": "verified", "Elo1978": "verified",
                                                       "Hunter2004": "verified"}
    assert rep.report_path.name == "bib_audit_semantic.md"
    text = rep.report_path.read_text(encoding="utf-8")
    doi = text.split("## DOI verification", 1)[1].split("\n## ", 1)[0]
    assert "| Key | Status | Source | Evidence |" in doi
    for key in ("Bradley1952", "Elo1978", "Hunter2004"):
        assert re.search(rf"^\| {key} \| verified \| crossref \|", doi, re.M)
    assert "FernandezNavarro2016" not in doi  # cited entries only
    assert _ids(rep).get("bib.no_doi.Elo1978") == "INFO"


def test_unreachable_api_is_warn_not_fail(sample_paper, cfg, cache):
    rep = validate_bib.run(sample_paper, cfg, semantic=True, fetch=unreachable_fetch, cache_path=cache, delay_s=0)
    assert rep.verdict == "PASS"
    ids = _ids(rep)
    assert ids["bib.lookup.unreachable.Bradley1952"] == "WARN"
    assert not any(s == "FAIL" for s in ids.values())
    assert gate.load(sample_paper, cfg)["checks"]["bib"]["status"] == "PASS"


def test_lookup_missing_is_fail(sample_paper, cfg, cache):
    rep = validate_bib.run(sample_paper, cfg, semantic=True, fetch=missing_fetch, cache_path=cache, delay_s=0)
    assert rep.verdict == "FAIL"
    assert _ids(rep)["bib.lookup.missing.Elo1978"] == "FAIL"


def test_skip_doi_makes_no_lookups(sample_paper, cfg, cache):
    def boom(url, headers):
        raise AssertionError("network used")
    rep = validate_bib.run(sample_paper, cfg, semantic=True, skip_doi=True, fetch=boom, cache_path=cache)
    assert rep.lookups == [] and rep.verdict == "PASS"
    text = rep.report_path.read_text(encoding="utf-8")
    assert "--skip-doi" in text.split("## DOI verification", 1)[1].split("\n## ", 1)[0]


def test_lookup_cap_from_limits(sample_paper, cache):
    p = sample_paper / "ploma.yaml"
    p.write_text(p.read_text(encoding="utf-8") + "limits:\n  doi_lookups_per_run: 1\n", encoding="utf-8")
    import ploma_config
    cfg = ploma_config.load(sample_paper)
    rep = validate_bib.run(sample_paper, cfg, semantic=True, fetch=verifying_fetch(sample_paper / "refs.bib"),
                           cache_path=cache, delay_s=0)
    statuses = [r.status for r in rep.lookups]
    assert statuses.count("skipped") == 2 and rep.verdict == "PASS"


@pytest.mark.parametrize("semantic", [False, True])
def test_report_matches_sample_format(sample_paper, cfg, cache, semantic):
    rep = validate_bib.run(sample_paper, cfg, semantic=semantic, fetch=verifying_fetch(sample_paper / "refs.bib"),
                           cache_path=cache, delay_s=0)
    text = rep.report_path.read_text(encoding="utf-8")
    positions = [text.find(h) for h in SAMPLE_HEADINGS]
    assert all(p >= 0 for p in positions) and positions == sorted(positions)
    assert "| Check | Critical | Medium | Low |" in text
    assert re.search(r"^\*\*Verdict: (PASS|FAIL)\.\*\*", text, re.M)
    assert text.startswith("# Bibliography " + ("Semantic" if semantic else "Structural") + " Audit")


def test_to_dict_is_json(sample_paper, cfg):
    d = json.loads(json.dumps(validate_bib.run(sample_paper, cfg, semantic=False).to_dict()))
    assert d["verdict"] == "PASS" and d["mode"] == "structural"


def test_cli(sample_paper, monkeypatch, capsys, cache):
    monkeypatch.setattr(validate_bib.cite_lookup, "default_cache_path", lambda: cache)
    assert validate_bib.main(["--root", str(sample_paper), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["verdict"] == "PASS"
    assert validate_bib.main(["--root", str(sample_paper)]) == 0
    assert "Verdict: PASS" in capsys.readouterr().out
    assert validate_bib.main(["--root", str(sample_paper / "nope")]) == 2


def test_cli_passes_keys_and_ignores_unsubstituted_placeholders(sample_paper, monkeypatch, cache):
    seen = {}
    real_run = validate_bib.run

    def fake_run(root, cfg, **kw):
        seen.update(kw)
        return real_run(root, cfg, semantic=False)
    monkeypatch.setattr(validate_bib, "run", fake_run)
    monkeypatch.delenv("OPENALEX_API_KEY", raising=False)
    monkeypatch.delenv("CLAUDE_PLUGIN_OPTION_OPENALEX_API_KEY", raising=False)
    validate_bib.main(["--root", str(sample_paper), "--semantic", "--mailto", "a@b.org", "--s2-key", "S2",
                       "--openalex-key", "${user_config.openalex_api_key}"])
    assert seen["semantic"] is True and seen["mailto"] == "a@b.org"
    assert seen["keys"] == {"semantic_scholar": "S2"}


def _doi_fetch(transform):
    """Crossref answers DOI lookups with the sample entry as transformed; searches find nothing."""
    entries = parse_bib((Path(__file__).resolve().parent.parent / "examples" / "sample-paper" / "refs.bib")
                        .read_text(encoding="utf-8"))
    by_doi = {e.fields["doi"].lower(): e for e in entries if e.fields.get("doi")}

    def fetch(url, headers):
        u = urlparse(url)
        if u.netloc == "api.crossref.org" and u.path.startswith("/works/"):
            e = by_doi.get(unquote(u.path[len("/works/"):]).lower())
            return (200, json.dumps({"message": transform(_item(e))})) if e else (404, "")
        return missing_fetch(url, headers)
    return fetch


def test_lookup_mismatch_is_fail(sample_paper, cfg, cache):
    def other_work(item):
        item["title"] = ["Deep Reinforcement Learning for Protein Folding Simulations"]
        return item
    rep = validate_bib.run(sample_paper, cfg, semantic=True, fetch=_doi_fetch(other_work), cache_path=cache, delay_s=0)
    assert _ids(rep)["bib.lookup.mismatch.Hunter2004"] == "FAIL"
    assert rep.verdict == "FAIL"
    assert gate.load(sample_paper, cfg)["checks"]["bib"]["status"] == "FAIL"


def test_lookup_partial_is_warn(sample_paper, cfg, cache):
    def wrong_year(item):
        item["issued"] = {"date-parts": [[item["issued"]["date-parts"][0][0] + 6]]}
        return item
    rep = validate_bib.run(sample_paper, cfg, semantic=True, fetch=_doi_fetch(wrong_year), cache_path=cache, delay_s=0)
    ids = _ids(rep)
    assert ids["bib.lookup.partial.Hunter2004"] == "WARN" and ids["bib.lookup.partial.Bradley1952"] == "WARN"
    assert not any(k.startswith("bib.lookup.") and v == "FAIL" for k, v in ids.items() if "Elo1978" not in k)


def _set_limit(root: Path, value: str):
    import ploma_config
    p = root / "ploma.yaml"
    p.write_text(p.read_text(encoding="utf-8") + f"limits:\n  doi_lookups_per_run: {value}\n", encoding="utf-8")
    return ploma_config.load(root)


def test_zero_lookup_cap_means_no_lookups(sample_paper, cache):
    """R89: an explicit 0 is not coerced to the default 50."""
    cfg = _set_limit(sample_paper, "0")

    def boom(url, headers):
        raise AssertionError("network used")
    rep = validate_bib.run(sample_paper, cfg, semantic=True, fetch=boom, cache_path=cache, delay_s=0)
    assert [r.status for r in rep.lookups] == ["skipped"] * 3 and rep.verdict == "PASS"


def test_non_integer_lookup_cap_is_usage_error(sample_paper, capsys):
    _set_limit(sample_paper, "lots")
    assert validate_bib.main(["--root", str(sample_paper), "--semantic", "--skip-doi"]) == 2
    assert "limits.doi_lookups_per_run" in capsys.readouterr().err


def test_cache_defaults_under_root_without_plugin_data(sample_paper, cfg, tmp_path, monkeypatch):
    """R86: CLAUDE_PLUGIN_DATA unset and cwd elsewhere: the cache lands in <root>/.ploma, not in cwd."""
    monkeypatch.delenv("CLAUDE_PLUGIN_DATA", raising=False)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    validate_bib.run(sample_paper, cfg, semantic=True, fetch=verifying_fetch(sample_paper / "refs.bib"), delay_s=0)
    assert (sample_paper / ".ploma" / "cite_lookup.json").is_file()
    assert not (elsewhere / ".ploma").exists()


def test_cache_uses_plugin_data_when_set(sample_paper, cfg, tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path / "pdata"))
    validate_bib.run(sample_paper, cfg, semantic=True, fetch=verifying_fetch(sample_paper / "refs.bib"), delay_s=0)
    assert (tmp_path / "pdata" / "cache" / "cite_lookup.json").is_file()
    assert not (sample_paper / ".ploma").exists()


# ---------------------------------------------------------------- final fix wave (R94, time budget)

def _retype(root: Path, key: str, new_type: str) -> None:
    p = root / "refs.bib"
    text = p.read_text(encoding="utf-8")
    old = re.search(r"@\w+\{" + re.escape(key) + ",", text).group(0)
    p.write_text(text.replace(old, f"@{new_type}{{{key},"), encoding="utf-8")


def test_misc_not_found_is_warn_not_indexed(sample_paper, cfg, cache):
    _retype(sample_paper, "Elo1978", "misc")
    rep = validate_bib.run(sample_paper, cfg, semantic=True, fetch=missing_fetch, cache_path=cache, delay_s=0)
    ids = _ids(rep)
    assert ids["bib.lookup.not_indexed.Elo1978"] == "WARN"
    assert "bib.lookup.missing.Elo1978" not in ids
    f = next(f for f in rep.findings if f.id == "bib.lookup.not_indexed.Elo1978")
    assert "not found in citation indexes (type misc)" in f.summary
    assert "bib.lookup.not_indexed.Elo1978" in rep.report_path.read_text(encoding="utf-8")


def test_article_not_found_all_sources_answering_is_fail(sample_paper, cfg, cache):
    rep = validate_bib.run(sample_paper, cfg, semantic=True, fetch=missing_fetch, cache_path=cache, delay_s=0)
    assert _ids(rep)["bib.lookup.missing.Bradley1952"] == "FAIL" and rep.verdict == "FAIL"


def test_article_not_found_with_one_source_429_is_warn(sample_paper, cfg, cache):
    def s2_rate_limited(url, headers):
        if "semanticscholar" in url:
            return 429, ""
        return missing_fetch(url, headers)
    rep = validate_bib.run(sample_paper, cfg, semantic=True, fetch=s2_rate_limited, cache_path=cache, delay_s=0)
    ids = _ids(rep)
    assert ids["bib.lookup.not_indexed.Bradley1952"] == "WARN"
    assert not any(v == "FAIL" for k, v in ids.items() if k.startswith("bib.lookup."))
    assert rep.verdict == "PASS"


def test_time_budget_skips_and_report_counts_them(sample_paper, cfg, cache):
    clock = {"t": 0.0}

    def slow(url, headers):
        clock["t"] += 200
        return verifying_fetch(sample_paper / "refs.bib")(url, headers)
    rep = validate_bib.run(sample_paper, cfg, semantic=True, fetch=slow, cache_path=cache, delay_s=0,
                           time_budget_s=150, clock=lambda: clock["t"])
    skipped = [r for r in rep.lookups if r.status == "skipped"]
    assert len(skipped) == len(rep.lookups) - 1 and skipped[0].evidence == "time budget reached"
    text = rep.report_path.read_text(encoding="utf-8")
    assert f"{len(skipped)} cited entries skipped (time budget reached)" in text


def test_validate_bib_default_time_budget_is_480():
    import inspect
    assert inspect.signature(validate_bib.run).parameters["time_budget_s"].default == 480


def test_unicode_spaces_in_api_titles_render_as_plain_spaces(sample_paper, cfg, cache):
    """R127 D2: NBSP, thin and narrow NBSP from API titles never reach the report as escapes or raw characters."""
    def spaced(item):
        item["title"] = [item["title"][0].replace(" ", " ", 1).replace(" ", " ", 1).replace(" ", " ", 1)
                         + " Extra"]
        return item
    rep = validate_bib.run(sample_paper, cfg, semantic=True, fetch=_doi_fetch(spaced), cache_path=cache, delay_s=0)
    text = rep.report_path.read_text(encoding="utf-8")
    assert "Extra" in text
    for bad in ("\\xa0", "\\u2009", "\\u202f", " ", " ", " "):
        assert bad not in text, bad
    for r in rep.lookups:
        assert not any(c in r.evidence for c in "   ") and "\\xa0" not in r.evidence
