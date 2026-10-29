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


def test_one_source_unreachable_rest_miss_is_not_indexed():
    """R94: missing needs every source to answer; one source down gives not_indexed (WARN)."""
    fetch = fake_fetch({"api.crossref.org": (503, ""), "api.openalex.org": (200, OPENALEX_EMPTY),
                        "api.semanticscholar.org": (200, S2_EMPTY)})
    r = lookup(ENTRY_NO_DOI, fetch=fetch, cache={})
    assert r.status == "not_indexed"
    assert "not found in citation indexes (type inproceedings)" in r.evidence


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
    assert r.to_dict() == {"key": "k", "status": "verified", "source": "crossref", "evidence": "e", "doi": "10.1/x",
                           "doi_unresolved": False}


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
    assert r.status == "not_indexed"                    # R94: Crossref counts as not answering
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


# ---------------------------------------------------------------- final fix wave

DATACITE_ARXIV = (API / "datacite_arxiv.json").read_text(encoding="utf-8")
ALL_MISS = {"api.crossref.org/works?": (200, CROSSREF_MISS), "api.openalex.org": (200, OPENALEX_EMPTY),
            "api.semanticscholar.org": (200, S2_EMPTY)}


def _typed(entry_type: str, key: str = "K") -> object:
    return parse_bib(f"@{entry_type}{{{key}, author = {{Dana Lindqvist}}, title = {{An Unindexed Work}}, year = 2019}}")[0]


def test_misc_not_found_is_not_indexed():
    """R94: @misc is legitimately absent from citation indexes."""
    r = lookup(_typed("misc"), fetch=fake_fetch(ALL_MISS), cache={})
    assert r.status == "not_indexed"
    assert "not found in citation indexes (type misc)" in r.evidence


def test_article_not_found_with_all_sources_answering_is_missing():
    r = lookup(_typed("article"), fetch=fake_fetch(ALL_MISS), cache={})
    assert r.status == "missing"


def test_article_not_found_with_s2_rate_limited_is_missing():
    """D13: keyless Semantic Scholar answers 429 as a rule; Crossref and OpenAlex answering decides."""
    routes = dict(ALL_MISS, **{"api.semanticscholar.org": (429, "")})
    r = lookup(_typed("article"), fetch=fake_fetch(routes), cache={})
    assert r.status == "missing" and "1 of 3 sources did not answer" in r.evidence


def test_article_not_found_with_openalex_rate_limited_is_not_indexed():
    routes = dict(ALL_MISS, **{"api.openalex.org": (429, "")})
    cache: dict = {}
    r = lookup(_typed("article"), fetch=fake_fetch(routes), cache=cache)
    assert r.status == "not_indexed" and "type article" in r.evidence
    assert cache == {}, "a verdict limited by a failed source is not cached"


def test_every_strict_type_can_be_missing():
    for t in ("article", "inproceedings", "conference", "book", "incollection", "inbook", "phdthesis",
              "mastersthesis"):
        assert lookup(_typed(t), fetch=fake_fetch(ALL_MISS), cache={}).status == "missing", t
    for t in ("techreport", "online", "software", "unpublished"):
        assert lookup(_typed(t), fetch=fake_fetch(ALL_MISS), cache={}).status == "not_indexed", t


def test_cli_not_indexed_does_not_fail(tmp_path, monkeypatch, capsys):
    bib = tmp_path / "r.bib"
    bib.write_text("@misc{M, title = {An Unindexed Work}}\n", encoding="utf-8")
    monkeypatch.setattr(cite_lookup, "default_fetch", fake_fetch(ALL_MISS))
    monkeypatch.setenv("CLAUDE_PLUGIN_DATA", str(tmp_path / "data"))
    assert cite_lookup.main([str(bib), "--json"]) == 0


ARXIV_ENTRY = parse_bib(r"""@misc{Vaswani2017,
  author = {Vaswani, Ashish and Shazeer, Noam},
  title = {Attention Is All You Need},
  year = {2017},
  doi = {10.48550/arXiv.1706.03762}
}""")[0]


def test_crossref_404_checks_datacite_and_verifies_arxiv_doi():
    """R93: arXiv DOIs are registered with DataCite, not Crossref."""
    calls = []
    fetch = fake_fetch({"api.crossref.org/works/10.48550": (404, "Resource not found."),
                        "api.datacite.org/dois/10.48550/arxiv.1706.03762": (200, DATACITE_ARXIV)}, calls)
    r = lookup(ARXIV_ENTRY, fetch=fetch, cache={})
    assert (r.status, r.source) == ("verified", "datacite"), r.evidence
    assert r.doi == "10.48550/arxiv.1706.03762"
    assert [host(c) for c in calls] == ["api.crossref.org", "api.datacite.org"]


def test_datacite_record_with_other_title_is_mismatch():
    e = parse_bib(r"@misc{K, author = {Vaswani, Ashish}, title = {Protein Folding in Yeast}, year = 2017,"
                  r" doi = {10.48550/arXiv.1706.03762}}")[0]
    fetch = fake_fetch({"api.crossref.org/works/10.48550": (404, ""), "api.datacite.org": (200, DATACITE_ARXIV)})
    r = lookup(e, fetch=fetch, cache={})
    assert (r.status, r.source) == ("mismatch", "datacite")


def test_datacite_creator_name_without_family_name_is_used():
    body = json.loads(DATACITE_ARXIV)
    body["data"]["attributes"]["creators"] = [{"name": "Vaswani, Ashish"}]
    fetch = fake_fetch({"api.crossref.org/works/10.48550": (404, ""), "api.datacite.org": (200, json.dumps(body))})
    assert lookup(ARXIV_ENTRY, fetch=fetch, cache={}).status == "verified"


def test_datacite_404_falls_back_to_title_search():
    calls = []
    fetch = fake_fetch(dict(ALL_MISS, **{"api.crossref.org/works/10.48550": (404, ""),
                                         "api.datacite.org": (404, "")}), calls)
    r = lookup(ARXIV_ENTRY, fetch=fetch, cache={})
    assert [host(c) for c in calls] == ["api.crossref.org", "api.datacite.org", "api.crossref.org",
                                        "api.openalex.org", "api.semanticscholar.org"]
    assert "DOI not found on Crossref or DataCite" in r.evidence


def test_crossref_unreachable_does_not_query_datacite():
    calls = []
    fetch = fake_fetch({"api.crossref.org": (503, ""), "api.openalex.org": (200, OPENALEX_EMPTY),
                        "api.semanticscholar.org": (200, S2_EMPTY)}, calls)
    lookup(ARXIV_ENTRY, fetch=fetch, cache={})
    assert "api.datacite.org" not in [host(c) for c in calls]


def test_datacite_verdict_is_cached_and_replayed():
    cache: dict = {}
    fetch = fake_fetch({"api.crossref.org/works/10.48550": (404, ""), "api.datacite.org": (200, DATACITE_ARXIV)})
    first = lookup(ARXIV_ENTRY, fetch=fetch, cache=cache)
    calls = []
    second = lookup(ARXIV_ENTRY, fetch=recording_fetch(calls), cache=cache)
    assert calls == [] and second == first


class FakeClock:
    def __init__(self) -> None:
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t


def test_time_budget_skips_remaining_entries(tmp_path):
    clock = FakeClock()
    inner = recording_fetch([], miss_all=True)

    def slow_fetch(url, headers):
        clock.t += 100            # every network call takes 100 s on the fake clock
        return inner(url, headers)
    entries = parse_bib(r"""@article{A, title = {Graph Methods for Process Discovery}}
@article{B, title = {Second Title Here}}
@article{C, title = {Third Title Here}}""")
    out = run(entries, max_lookups=50, delay_s=0, cache_path=tmp_path / "c.json", mailto="", keys={},
              fetch=slow_fetch, time_budget_s=480, clock=clock)
    assert [r.status for r in out] == ["missing", "missing", "skipped"]
    assert out[2].evidence == "time budget reached"
    assert json.loads((tmp_path / "c.json").read_text()), "results found before the budget ran out are cached"


def test_time_budget_still_serves_cache_hits(tmp_path):
    path = tmp_path / "c.json"
    run([ENTRY_WITH_DOI], max_lookups=5, delay_s=0, cache_path=path, mailto="", keys={},
        fetch=fake_fetch({"api.crossref.org/works/10.1/x": (200, CROSSREF_HIT)}))
    clock = FakeClock()
    out = run([ENTRY_NO_DOI, ENTRY_WITH_DOI], max_lookups=5, delay_s=0, cache_path=path, mailto="", keys={},
              fetch=recording_fetch([], miss_all=True), time_budget_s=0, clock=clock)
    assert [r.status for r in out] == ["skipped", "verified"]


def test_default_time_budget_is_480_seconds():
    import inspect
    assert inspect.signature(run).parameters["time_budget_s"].default == 480


def test_cache_saved_every_five_network_lookups(tmp_path, monkeypatch):
    saves = []
    real = cite_lookup.save_cache
    monkeypatch.setattr(cite_lookup, "save_cache", lambda path, cache: (saves.append(len(cache)), real(path, cache)))
    entries = [_doi_entry("Sequence Models for Event Logs", doi=f"10.1/x{i}") for i in range(12)]
    for i, e in enumerate(entries):
        e.key = f"K{i}"
    body = {f"api.crossref.org/works/10.1/x{i}": (200, _work(title=["Sequence Models for Event Logs"]))
            for i in range(12)}
    run(entries, max_lookups=50, delay_s=0, cache_path=tmp_path / "c.json", mailto="", keys={}, fetch=fake_fetch(body))
    assert saves == [5, 10, 12]


def test_escaped_springer_doi_is_looked_up_unescaped():
    """R127 D1 falsification: an escaped Springer DOI resolves with the unescaped DOI in the requested URL."""
    e = parse_bib(r"""@inproceedings{Mueller2021,
  author = {M{\"u}ller, Ana and Okafor, Ben},
  title = {Sequence {Models} for Event Logs},
  year = {2021},
  doi = {10.1007/978-3-030-85469-0\_16}
}""")[0]
    hit = json.loads(CROSSREF_HIT)
    hit["message"]["DOI"] = "10.1007/978-3-030-85469-0_16"
    calls: list = []
    fetch = fake_fetch({"api.crossref.org/works/10.1007/978-3-030-85469-0_16": (200, json.dumps(hit))}, calls)
    r = lookup(e, fetch=fetch, cache={})
    assert r.status == "verified", r.evidence
    assert r.doi == "10.1007/978-3-030-85469-0_16"
    assert "\\" not in calls[0][0] and "%5C" not in calls[0][0]
    assert "/works/10.1007/978-3-030-85469-0_16" in calls[0][0]


# ---------------------------------------------------------------- D13, D14: field-fix unit 2

S2_429 = {"api.semanticscholar.org": (429, "")}
DEAD_DOI = {"api.crossref.org/works/10.9999": (404, "Resource not found."), "api.datacite.org": (404, "")}


def test_fabricated_article_with_fake_doi_is_missing_without_s2():
    e = parse_bib(r"@article{Fake2020, author = {Nobody, Ann}, title = {A Study That Was Never Written},"
                  r" year = 2020, doi = {10.9999/fake.123}}")[0]
    r = lookup(e, fetch=fake_fetch({**DEAD_DOI, **ALL_MISS, **S2_429}), cache={})
    assert r.status == "missing", r.evidence
    assert "DOI not found on Crossref or DataCite" in r.evidence and r.doi_unresolved is False


def test_dead_doi_and_no_match_among_answering_sources_is_missing():
    e = parse_bib(r"@inproceedings{Fake2020, author = {Nobody, Ann}, title = {A Study That Was Never Written},"
                  r" year = 2020, doi = {10.9999/fake.123}}")[0]
    routes = {**DEAD_DOI, **ALL_MISS, **S2_429, "api.openalex.org": (503, "")}
    assert lookup(e, fetch=fake_fetch(routes), cache={}).status == "missing"
    misc = parse_bib(r"@misc{Fake2020, title = {A Study That Was Never Written}, doi = {10.9999/fake.123}}")[0]
    assert lookup(misc, fetch=fake_fetch(routes), cache={}).status == "not_indexed"


def test_real_article_with_typo_doi_is_partial_and_doi_unresolved():
    e = parse_bib(r"""@article{Lind2019, author = {Dana Lindqvist}, title = {Graph Methods for Process Discovery},
      year = 2019, doi = {10.9999/typo}}""")[0]
    routes = dict(DEAD_DOI, **S2_429, **{"api.crossref.org/works?": (200, CROSSREF_MISS),
                                         "api.openalex.org": (200, OPENALEX_HIT)})
    r = lookup(e, fetch=fake_fetch(routes), cache={})
    assert (r.status, r.source) == ("partial", "openalex") and r.doi_unresolved is True


def test_doi_unresolved_only_when_both_registries_answer_404():
    e = parse_bib(r"""@article{Lind2019, author = {Dana Lindqvist}, title = {Graph Methods for Process Discovery},
      year = 2019, doi = {10.9999/typo}}""")[0]
    routes = {"api.crossref.org/works/10.9999": (404, ""), "api.datacite.org": (503, ""),
              "api.crossref.org/works?": (200, CROSSREF_MISS), "api.openalex.org": (200, OPENALEX_HIT)}
    assert lookup(e, fetch=fake_fetch(routes), cache={}).doi_unresolved is False
