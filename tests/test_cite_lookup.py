"""Tests for the citation existence lookup. Every test injects ``fetch``; nothing touches the network."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import cite_lookup
from bib_check import parse_bib
from cite_lookup import LookupResult, default_cache_path, lookup, run

API = Path(__file__).resolve().parent / "fixtures" / "api"
CROSSREF_HIT = (API / "crossref_hit.json").read_text(encoding="utf-8")
CROSSREF_SUBTITLE = (API / "crossref_subtitle.json").read_text(encoding="utf-8")
CROSSREF_MISS = (API / "crossref_miss.json").read_text(encoding="utf-8")
OPENALEX_HIT = (API / "openalex_hit.json").read_text(encoding="utf-8")
S2_HIT = (API / "s2_hit.json").read_text(encoding="utf-8")
OPENALEX_EMPTY = json.dumps({"meta": {"count": 0}, "results": []})
S2_EMPTY = json.dumps({"total": 0, "data": []})

ENTRY_WITH_DOI = parse_bib(r"""@article{Mueller2021,
  author = {M{\"u}ller, Ana and Okafor, Ben},
  title = {Sequence {Models} for Event Logs},
  year = {2021},
  doi = {https://doi.org/10.1/X}
}""")[0]
ENTRY_NO_DOI = parse_bib(r"""@inproceedings{Lind2019,
  author = {Dana Lindqvist and Eli Park},
  title = {Graph Methods for {P}rocess Discovery},
  year = 2019
}""")[0]


def fake_fetch(routes: dict[str, tuple[int, str]], calls: list | None = None):
    """Return the first route whose substring occurs in the URL; (404, "") otherwise."""
    def fetch(url: str, headers: dict) -> tuple[int, str]:
        if calls is not None:
            calls.append((url, dict(headers)))
        for needle, resp in routes.items():
            if needle in url:
                return resp
        return (404, "")
    return fetch


def recording_fetch(calls: list, miss_all: bool = False):
    routes = {"api.crossref.org": (200, CROSSREF_MISS), "api.openalex.org": (200, OPENALEX_EMPTY),
              "api.semanticscholar.org": (200, S2_EMPTY)} if miss_all else {}
    return fake_fetch(routes, calls)


def host(call) -> str:
    return urlparse(call[0]).netloc


def test_doi_hit_is_verified():
    r = lookup(ENTRY_WITH_DOI, fetch=fake_fetch({"api.crossref.org/works/10.1/x": (200, CROSSREF_HIT)}), cache={})
    assert r.status == "verified" and r.source == "crossref"
    assert r.key == "Mueller2021" and r.doi == "10.1/x"


def test_title_fallback_order():
    calls = []
    r = lookup(ENTRY_NO_DOI, fetch=recording_fetch(calls, miss_all=True), cache={})
    assert r.status == "missing"
    assert [host(c) for c in calls] == ["api.crossref.org", "api.openalex.org", "api.semanticscholar.org"]


def test_title_search_hit_on_openalex_is_verified():
    fetch = fake_fetch({"api.crossref.org": (200, CROSSREF_MISS), "api.openalex.org": (200, OPENALEX_HIT)})
    r = lookup(ENTRY_NO_DOI, fetch=fetch, cache={})
    assert (r.status, r.source, r.doi) == ("verified", "openalex", "10.5/ol")


def test_title_search_hit_on_semantic_scholar_is_verified():
    fetch = fake_fetch({"api.crossref.org": (200, CROSSREF_MISS), "api.openalex.org": (200, OPENALEX_EMPTY),
                        "api.semanticscholar.org": (200, S2_HIT)})
    r = lookup(ENTRY_NO_DOI, fetch=fetch, cache={})
    assert (r.status, r.source) == ("verified", "semantic_scholar")


def test_author_mismatch_is_partial():
    wrong_author = parse_bib(r"""@article{X, author = {Nobody, Zed}, title = {Graph Methods for Process Discovery},
      year = 2019}""")[0]
    fetch = fake_fetch({"api.crossref.org": (200, CROSSREF_MISS), "api.openalex.org": (200, OPENALEX_HIT)})
    r = lookup(wrong_author, fetch=fetch, cache={})
    assert (r.status, r.source) == ("partial", "openalex")
    assert "author" in r.evidence


def test_year_off_by_two_is_partial_and_off_by_one_is_verified():
    fetch = fake_fetch({"api.crossref.org/works/10.1/x": (200, CROSSREF_HIT)})
    for year, status in (("2022", "verified"), ("2023", "partial")):
        e = parse_bib(rf"""@article{{K, author = {{M{{\"u}}ller, Ana}}, title = {{Sequence Models for Event Logs}},
          year = {year}, doi = {{10.1/x}}}}""")[0]
        assert lookup(e, fetch=fetch, cache={}).status == status, year


def test_doi_hit_with_unrelated_title_is_mismatch():
    e = parse_bib(r"@article{K, author = {M{\"u}ller, Ana}, title = {Protein Folding in Yeast}, year = 2021, doi = {10.1/x}}")[0]
    r = lookup(e, fetch=fake_fetch({"api.crossref.org/works/10.1/x": (200, CROSSREF_HIT)}), cache={})
    assert (r.status, r.source) == ("mismatch", "crossref")


def test_all_unreachable():
    for status in (0, 429, 503):
        calls = []
        r = lookup(ENTRY_NO_DOI, fetch=fake_fetch({"api.": (status, "")}, calls), cache={})
        assert r.status == "unreachable", status
        assert len(calls) == 3        # each source tried once, no retries


def test_one_source_unreachable_rest_miss_is_missing():
    fetch = fake_fetch({"api.crossref.org": (503, ""), "api.openalex.org": (200, OPENALEX_EMPTY),
                        "api.semanticscholar.org": (200, S2_EMPTY)})
    assert lookup(ENTRY_NO_DOI, fetch=fetch, cache={}).status == "missing"


def test_cache_hit_skips_fetch():
    cache: dict = {}
    fetch = fake_fetch({"api.crossref.org/works/10.1/x": (200, CROSSREF_HIT)})
    first = lookup(ENTRY_WITH_DOI, fetch=fetch, cache=cache)
    assert list(cache) == ["doi:10.1/x"] and "checked_at" in cache["doi:10.1/x"]
    calls = []
    second = lookup(ENTRY_WITH_DOI, fetch=recording_fetch(calls), cache=cache)
    assert calls == [] and second == first


def test_stale_cache_is_refreshed():
    old = (datetime.now(timezone.utc) - timedelta(days=91)).isoformat()
    cache = {"doi:10.1/x": {"key": "Mueller2021", "status": "missing", "source": "", "evidence": "", "doi": "10.1/x",
                            "checked_at": old}}
    r = lookup(ENTRY_WITH_DOI, fetch=fake_fetch({"api.crossref.org/works/10.1/x": (200, CROSSREF_HIT)}), cache=cache)
    assert r.status == "verified" and cache["doi:10.1/x"]["checked_at"] != old


def test_unreachable_is_not_cached():
    cache: dict = {}
    lookup(ENTRY_NO_DOI, fetch=fake_fetch({"api.": (0, "")}), cache=cache)
    assert cache == {}


def test_max_lookups_marks_skipped(tmp_path):
    entries = parse_bib(r"""@article{A, title = {Graph Methods for Process Discovery}}
@article{B, title = {Second Title Here}}
@article{C, title = {Third Title Here}}""")
    calls = []
    out = run(entries, max_lookups=2, delay_s=0, cache_path=tmp_path / "c.json", mailto="", keys={},
              fetch=recording_fetch(calls, miss_all=True))
    assert [r.key for r in out] == ["A", "B", "C"]
    assert [r.status for r in out] == ["missing", "missing", "skipped"]
    assert len(calls) == 6


def test_run_persists_cache_and_reuses_it(tmp_path):
    path = tmp_path / "sub" / "c.json"
    fetch = fake_fetch({"api.crossref.org/works/10.1/x": (200, CROSSREF_HIT)})
    run([ENTRY_WITH_DOI], max_lookups=5, delay_s=0, cache_path=path, mailto="", keys={}, fetch=fetch)
    record = json.loads(path.read_text())["doi:10.1/x"]
    assert record["doi"]["hit"]["title"] == "Sequence Models for Event Logs" and "checked_at" in record
    calls = []
    out = run([ENTRY_WITH_DOI], max_lookups=0, delay_s=0, cache_path=path, mailto="", keys={},
              fetch=recording_fetch(calls))
    assert calls == [] and out[0].status == "verified"      # cache hits do not count against max_lookups


def test_mailto_is_sent_to_crossref():
    calls = []
    lookup(ENTRY_WITH_DOI, fetch=fake_fetch({"api.crossref.org": (200, CROSSREF_HIT)}, calls), mailto="me@x.org", cache={})
    lookup(ENTRY_NO_DOI, fetch=recording_fetch(calls, miss_all=True), mailto="me@x.org", cache={})
    crossref = [c for c in calls if host(c) == "api.crossref.org"]
    assert len(crossref) == 2
    for url, headers in crossref:
        assert parse_qs(urlparse(url).query)["mailto"] == ["me@x.org"]


def test_title_search_urls_and_api_keys():
    calls = []
    lookup(ENTRY_NO_DOI, fetch=recording_fetch(calls, miss_all=True), mailto="m@x.org",
           keys={"openalex": "OAK", "semantic_scholar": "S2K"}, cache={})
    cr, oa, s2 = calls
    assert parse_qs(urlparse(cr[0]).query) == {"query.bibliographic": ["Graph Methods for Process Discovery"],
                                               "rows": ["3"], "mailto": ["m@x.org"]}
    q = parse_qs(urlparse(oa[0]).query)
    assert q["search"] == ["Graph Methods for Process Discovery"] and q["per-page"] == ["3"]
    assert q["api_key"] == ["OAK"] and q["mailto"] == ["m@x.org"]
    assert urlparse(s2[0]).path == "/graph/v1/paper/search"
    assert parse_qs(urlparse(s2[0]).query)["fields"] == ["title,authors,year,externalIds"]
    assert s2[1].get("x-api-key") == "S2K"
    assert "x-api-key" not in oa[1]


def test_entry_without_doi_or_title_is_skipped():
    calls = []
    r = lookup(parse_bib("@misc{K, author = {A, B}}")[0], fetch=recording_fetch(calls), cache={})
    assert r.status == "skipped" and calls == []


def test_helpers():
    assert cite_lookup.norm_title(r"The {\'E}cole \emph{Approach}: A--B!") == "the ecole approach a b"
    assert cite_lookup.first_family(r"M{\"u}ller, Ana and Okafor, Ben") == "muller"
    assert cite_lookup.first_family("Dana van Lindqvist and Eli Park") == "lindqvist"
    assert cite_lookup.first_family("{The Ranking Group}") == "the ranking group"


def test_default_cache_path(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path))
    assert default_cache_path() == tmp_path / "cache" / "cite_lookup.json"
    monkeypatch.delenv("CLAUDE_PLUGIN_DATA")
    monkeypatch.chdir(tmp_path)
    assert default_cache_path() == tmp_path / ".ploma" / "cite_lookup.json"


def test_default_fetch_never_raises():
    status, body = cite_lookup.default_fetch("http://127.0.0.1:9/nothing", {})
    assert (status, body) == (0, "")


def _cli_env(monkeypatch, tmp_path, routes):
    monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path / "data"))
    monkeypatch.setattr(cite_lookup, "default_fetch", fake_fetch(routes))


def test_cli_json_and_exit_codes(tmp_path, monkeypatch, capsys):
    _cli_env(monkeypatch, tmp_path, {"api.crossref.org/works/10.1/x": (200, CROSSREF_HIT),
                                     "api.crossref.org/works?": (200, CROSSREF_MISS),
                                     "api.openalex.org": (200, OPENALEX_EMPTY), "api.semanticscholar.org": (200, S2_EMPTY)})
    bib = tmp_path / "refs.bib"
    bib.write_text(r"""@article{Mueller2021, author = {M{\"u}ller, Ana}, title = {Sequence Models for Event Logs},
  year = 2021, doi = {10.1/x}}
@article{Ghost, author = {Nobody, Zed}, title = {A Paper That Does Not Exist}, year = 2020}""")
    assert cite_lookup.main([str(bib), "--keys", "Mueller2021", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert [(r["key"], r["status"]) for r in data["results"]] == [("Mueller2021", "verified")]
    assert cite_lookup.main([str(bib)]) == 1
    out = capsys.readouterr().out
    assert "Ghost" in out and "missing" in out and "crossref" in out


def test_cli_unreadable_bib_is_usage_error(tmp_path):
    assert cite_lookup.main([str(tmp_path / "nope.bib")]) == 2
    assert cite_lookup.main(["--bogus"]) == 2


def test_lookup_result_to_dict():
    r = LookupResult("k", "verified", "crossref", "e", "10.1/x")
    assert r.to_dict() == {"key": "k", "status": "verified", "source": "crossref", "evidence": "e", "doi": "10.1/x"}


def test_doi_not_found_falls_back_to_title_search_as_partial():
    e = parse_bib(r"""@inproceedings{K, author = {Dana Lindqvist}, title = {Graph Methods for Process Discovery},
      year = 2019, doi = {10.0/broken}}""")[0]
    fetch = fake_fetch({"api.crossref.org/works/10.0/broken": (404, "Resource not found."),
                        "api.crossref.org/works?": (200, CROSSREF_MISS), "api.openalex.org": (200, OPENALEX_HIT)})
    r = lookup(e, fetch=fetch, cache={})
    assert (r.status, r.source) == ("partial", "openalex") and "DOI not found" in r.evidence


def test_run_default_fetch_sends_user_agent_with_mailto(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(cite_lookup, "default_fetch", fake_fetch({"api.crossref.org": (200, CROSSREF_HIT)}, calls))
    run([ENTRY_WITH_DOI], max_lookups=5, delay_s=0, cache_path=tmp_path / "c.json", mailto="me@x.org", keys={})
    assert calls[0][1]["User-Agent"] == "ploma/0.1 (mailto:me@x.org)"


def test_delay_only_between_network_calls(tmp_path, monkeypatch):
    sleeps = []
    monkeypatch.setattr(cite_lookup.time, "sleep", sleeps.append)
    path = tmp_path / "c.json"
    fetch = fake_fetch({"api.crossref.org/works/10.1/x": (200, CROSSREF_HIT)})
    run([ENTRY_WITH_DOI], max_lookups=5, delay_s=0.5, cache_path=path, mailto="", keys={}, fetch=fetch)
    assert sleeps == []                                   # a single call needs no delay
    run([ENTRY_WITH_DOI, ENTRY_NO_DOI], max_lookups=5, delay_s=0.5, cache_path=path, mailto="", keys={},
        fetch=recording_fetch([], miss_all=True))
    assert sleeps == [0.5, 0.5]                           # cache hit free; three title-search calls, two gaps


# ---------------------------------------------------------------- fix round 1

def _doi_entry(title: str, author: str = r"M{\"u}ller, Ana", year: str = "2021", doi: str = "10.1/x"):
    return parse_bib(f"@article{{K, author = {{{author}}}, title = {{{title}}}, year = {year}, doi = {{{doi}}}}}")[0]


def _work(**message) -> str:
    return json.dumps({"status": "ok", "message": {"DOI": "10.1/x", **message}})


def test_hit_without_author_or_year_is_verified():
    fetch = fake_fetch({"api.crossref.org/works/10.1/x": (200, _work(title=["Sequence Models for Event Logs"]))})
    r = lookup(_doi_entry("Sequence Models for Event Logs"), fetch=fetch, cache={})
    assert r.status == "verified", r.evidence


def test_crossref_subtitle_is_joined_and_verified():
    e = _doi_entry("Process Mining: Discovery, Conformance and Enhancement of Business Processes",
                   author="van der Aalst, Wil", year="2011", doi="10.2/pm")
    r = lookup(e, fetch=fake_fetch({"api.crossref.org/works/10.2/pm": (200, CROSSREF_SUBTITLE)}), cache={})
    assert (r.status, r.source) == ("verified", "crossref"), r.evidence


def test_bib_subtitle_against_bare_crossref_title_is_verified():
    fetch = fake_fetch({"api.crossref.org/works/10.1/x": (200, _work(title=["Deep Learning"],
                                                                      issued={"date-parts": [[2021]]}))})
    r = lookup(_doi_entry("Deep Learning: A Survey", author="Ana Muller"), fetch=fetch, cache={})
    assert r.status == "verified", r.evidence


def test_cached_facts_are_rejudged_after_bib_fix():
    cache: dict = {}
    bad = _doi_entry("Protein Folding in Yeast")
    first = lookup(bad, fetch=fake_fetch({"api.crossref.org/works/10.1/x": (200, CROSSREF_HIT)}), cache=cache)
    assert first.status == "mismatch"

    def must_not_fetch(url, headers):
        raise AssertionError(f"fetched {url}")
    fixed = _doi_entry("Sequence Models for Event Logs")
    assert lookup(fixed, fetch=must_not_fetch, cache=cache).status == "verified"


def test_unexpected_shapes_count_as_source_failure():
    empty = {"api.openalex.org": (200, OPENALEX_EMPTY), "api.semanticscholar.org": (200, S2_EMPTY)}
    r = lookup(ENTRY_NO_DOI, fetch=fake_fetch({"api.crossref.org": (200, json.dumps({"message": {"items": ["x"]}})),
                                               **empty}), cache={})
    assert r.status == "missing"
    r = lookup(_doi_entry("Sequence Models for Event Logs"),
               fetch=fake_fetch({"api.crossref.org/works/10.1/x": (200, _work(title=[None]))}), cache={})
    assert r.status == "partial"                        # parsed as an empty title, no TypeError
    for body in (_work(title=["Sequence Models for Event Logs"], author=["x"]), "not json", "[1, 2]"):
        r = lookup(_doi_entry("Sequence Models for Event Logs"),
                   fetch=fake_fetch({"api.crossref.org/works/10.1/x": (200, body), "api.crossref.org/works?": (503, ""),
                                     "api.": (503, "")}), cache={})
        assert r.status == "unreachable", body


def test_run_survives_exception_per_entry_and_saves_cache(tmp_path):
    def fetch(url, headers):
        if "10.1/x" in url:
            return (200, CROSSREF_HIT)
        raise RuntimeError("boom")
    path = tmp_path / "c.json"
    out = run([ENTRY_NO_DOI, ENTRY_WITH_DOI], max_lookups=5, delay_s=0, cache_path=path, mailto="", keys={}, fetch=fetch)
    assert out[0].status == "unreachable" and "boom" in out[0].evidence
    assert out[1].status == "verified"
    assert "doi:10.1/x" in json.loads(path.read_text())


def test_html_tags_are_stripped_from_titles():
    assert cite_lookup.norm_title("<i>In vivo</i> imaging of H<sub>2</sub>O") == "in vivo imaging of h2o"
    fetch = fake_fetch({"api.crossref.org/works/10.1/x": (200, _work(title=["<i>Sequence Models</i>"]))})
    assert lookup(_doi_entry("Sequence Models"), fetch=fetch, cache={}).status == "verified"


# ---------------------------------------------------------------- fix round 2

def test_doi_record_without_title_is_partial():
    for title in ([None], []):
        fetch = fake_fetch({"api.crossref.org/works/10.1/x": (200, _work(title=title))})
        r = lookup(_doi_entry("Sequence Models for Event Logs"), fetch=fetch, cache={})
        assert (r.status, r.evidence) == ("partial", "DOI resolves but the record has no title"), title


def test_both_sides_with_different_subtitles_is_partial():
    e = _doi_entry("Process Mining: Data Science in Action", author="van der Aalst, Wil", year="2011", doi="10.2/pm")
    r = lookup(e, fetch=fake_fetch({"api.crossref.org/works/10.2/pm": (200, CROSSREF_SUBTITLE)}), cache={})
    assert r.status == "partial" and "subtitle differs" in r.evidence, r.evidence


def test_record_with_subtitle_against_bare_bib_title_is_verified():
    e = _doi_entry("Process Mining", author="van der Aalst, Wil", year="2011", doi="10.2/pm")
    r = lookup(e, fetch=fake_fetch({"api.crossref.org/works/10.2/pm": (200, CROSSREF_SUBTITLE)}), cache={})
    assert r.status == "verified", r.evidence


def test_title_search_with_different_subtitles_is_partial():
    body = json.dumps({"results": [{"title": "Graph Methods: A Primer", "publication_year": 2019,
                                    "authorships": [{"author": {"display_name": "Dana Lindqvist"}}]}]})
    e = parse_bib("@article{K, author = {Dana Lindqvist}, title = {Graph Methods: Theory and Practice}, year = 2019}")[0]
    fetch = fake_fetch({"api.crossref.org": (200, CROSSREF_MISS), "api.openalex.org": (200, body)})
    r = lookup(e, fetch=fetch, cache={})
    assert (r.status, r.source) == ("partial", "openalex") and "subtitle differs" in r.evidence
