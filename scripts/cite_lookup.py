"""Citation existence lookup: Crossref by DOI (DataCite when Crossref does not know the DOI), else title
search on Crossref, OpenAlex, Semantic Scholar.

Usage: python3 scripts/cite_lookup.py <refs.bib> [--keys k1,k2] [--max 50] [--mailto x]
       [--openalex-key K] [--s2-key K] [--json]
Statuses: verified, partial, mismatch, missing, not_indexed, unreachable, skipped.
``missing`` needs an entry type that citation indexes cover (STRICT_TYPES) and either a DOI that both
Crossref and DataCite answer 404 for with no title match among the sources that answered, or (R168) all three
sources answering without a title match on an entry with no grey-literature marker (grey_marker: report,
working paper or thesis wording, a Citeseer publisher, a report or thesis type, proceedings with neither DOI
nor ISBN); otherwise a work no source knows is ``not_indexed`` (R94), so keyless Semantic Scholar's 429 (D13)
leaves a DOI-less entry a WARN. A title-matched entry whose DOI both registries answer 404 for is ``partial``
with ``doi_unresolved`` set (D14). Theses (ALL_SOURCES_TYPES) with a dead DOI are missing only when all three
sources answered (R165). A 200 with an empty or unreadable body counts as not answering.
Results are cached for 90 days in ``default_cache_path()``; run() saves the cache every
SAVE_EVERY network lookups and skips the remaining network lookups once its time budget is spent.
Exit codes: 0 no result is missing or mismatch, 1 at least one is, 2 usage error or unreadable bib file.
This is the only ploma script that uses the network.
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import sys
import tempfile
import time
import unicodedata
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable
from urllib.parse import quote, urlencode

from bib_check import Entry, _norm_doi, parse_bib

Fetch = Callable[[str, dict], "tuple[int, str]"]

STATUSES = ("verified", "partial", "mismatch", "missing", "not_indexed", "unreachable", "skipped")
# Entry types that citation indexes are expected to cover; others (misc, techreport, online, software) may be absent.
STRICT_TYPES = frozenset({"article", "inproceedings", "conference", "book", "incollection", "inbook",
                          "phdthesis", "mastersthesis"})
# Strict types whose dead-DOI rule needs all three sources (R165): Crossref and OpenAlex list theses poorly, so a
# thesis with a dead DOI is missing only when all three sources answered without a match.
ALL_SOURCES_TYPES = frozenset({"phdthesis", "mastersthesis"})
# R168: wording in these fields, publishers and entry types that mark grey literature, which indexes list poorly.
GREY_FIELDS = ("journal", "booktitle", "institution", "type", "note")
# Whole words only, singular "report": "Scientific Reports" and "Synthesis Lectures" are journals, not grey.
GREY_WORDS_RE = re.compile(r"tech\.\s*rep|\b(?:technical report|working paper|report|thesis|dissertation|wp)\b", re.I)
GREY_PUBLISHER_FIELDS = ("publisher", "organization", "howpublished")
GREY_PUBLISHER_RE = re.compile(r"citeseer", re.I)
GREY_TYPES = frozenset({"techreport", "misc", "unpublished", "phdthesis", "mastersthesis"})
PROCEEDINGS_TYPES = frozenset({"inproceedings", "conference", "proceedings"})
SAVE_EVERY = 5
TIME_BUDGET_S = 480
TITLE_MATCH = 0.90
TITLE_MISMATCH = 0.6
CACHE_MAX_AGE = timedelta(days=90)
USER_AGENT = "ploma/0.1"
TIMEOUT_S = 10
NOT_CACHED = {"unreachable", "skipped"}  # never cached, and a replay giving these refetches


@dataclass
class LookupResult:
    key: str
    status: str
    source: str = ""
    evidence: str = ""
    doi: str = ""
    doi_unresolved: bool = False  # the entry's DOI is unknown to Crossref and DataCite (both answered 404)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class _Hit:
    title: str
    authors: list[str]
    year: int | None
    doi: str

    def __post_init__(self) -> None:
        self.title = plain_spaces(self.title)
        self.authors = [plain_spaces(a) for a in self.authors]


_SPACES_RE = re.compile("[\u00a0\u2000-\u200a\u202f\u205f\u3000]")


def plain_spaces(text: str) -> str:
    """NBSP, thin, narrow NBSP and other Unicode spaces as a plain space (R127 D2)."""
    return _SPACES_RE.sub(" ", text or "")


# ---------------------------------------------------------------- normalisation

def _plain(text: str) -> str:
    """Lowercase ASCII text with HTML/JATS tags, LaTeX commands, braces and accents removed; non-alphanumerics become spaces."""
    text = re.sub(r"<[^>]+>", "", str(text or ""))
    text = re.sub(r"\\[A-Za-z]+\s*|\\.", "", text)
    text = unicodedata.normalize("NFKD", text.replace("{", "").replace("}", ""))
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    return re.sub(r"[^0-9a-z]+", " ", text).strip()


def norm_title(title: str) -> str:
    return _plain(title)


def query_title(title: str) -> str:
    """Title as sent to search APIs: LaTeX commands and braces dropped, case kept, whitespace collapsed."""
    text = re.sub(r"\\[A-Za-z]+\s*|\\.", "", title).replace("{", "").replace("}", "")
    return " ".join(text.split())


def first_family(author: str) -> str:
    """Normalised family name of the first author ("Last, First", "First Last" or a braced corporate name)."""
    first = re.split(r"\s+and\s+", author.strip(), maxsplit=1)[0].strip()
    if not first:
        return ""
    if first.startswith("{") and first.endswith("}") and "," not in first:
        return _plain(first)
    if "," in first:
        return _plain(first.split(",", 1)[0])
    words = _plain(first).split()
    return words[-1] if words else ""


def _year(text: str) -> int | None:
    m = re.search(r"\d{4}", text or "")
    return int(m.group(0)) if m else None


_SUBTITLE_RE = re.compile(r":| - ")


def _split_title(title: str) -> tuple[str, bool]:
    """(part before the first colon or " - ", whether a subtitle follows)."""
    parts = _SUBTITLE_RE.split(title, maxsplit=1)
    return parts[0], len(parts) > 1 and bool(norm_title(parts[1]))


def _compare_titles(a: str, b: str) -> tuple[float, str]:
    """(similarity, problem). The similarity is the max of the full-title ratio and the ratio of the parts before
    the first colon. The main-title ratio may verify only when at most one side has a subtitle; when both have
    subtitles that differ (full ratio < 0.90), a matching main title is reported with a "subtitle differs" problem."""
    full = difflib.SequenceMatcher(None, norm_title(a), norm_title(b)).ratio()
    (ma, sa), (mb, sb) = _split_title(a), _split_title(b)
    ma, mb = norm_title(ma), norm_title(mb)
    main = difflib.SequenceMatcher(None, ma, mb).ratio() if ma and mb else 0.0
    if main <= full:
        return full, ""
    if sa and sb and full < TITLE_MATCH:
        return main, "subtitle differs"
    return main, ""


def _ratio(a: str, b: str) -> float:
    return _compare_titles(a, b)[0]


# ---------------------------------------------------------------- response parsing
# Parsers may raise on unexpected shapes; callers treat any exception as that source failing.

def _first(value) -> str:
    if isinstance(value, list):
        value = value[0] if value else ""
    return value if isinstance(value, str) else ""


def _crossref_item(item: dict) -> _Hit:
    title = _first(item.get("title"))
    subtitle = _first(item.get("subtitle"))
    if subtitle:
        title = f"{title}: {subtitle}"
    authors = [" ".join(p for p in (a.get("given") or "", a.get("family") or "") if p) or a.get("name") or ""
               for a in item.get("author") or []]
    year = None
    for k in ("issued", "published", "published-print", "published-online"):
        parts = (item.get(k) or {}).get("date-parts") or [[None]]
        if parts and parts[0] and parts[0][0]:
            year = int(parts[0][0])
            break
    return _Hit(title, authors, year, _norm_doi(item.get("DOI") or ""))


def _crossref_search(data: dict) -> list[_Hit]:
    return [_crossref_item(i) for i in (data.get("message") or {}).get("items") or []]


def _openalex(data: dict) -> list[_Hit]:
    out = []
    for r in data.get("results") or []:
        authors = [((a.get("author") or {}).get("display_name") or "") for a in r.get("authorships") or []]
        year = r.get("publication_year")
        out.append(_Hit(r.get("title") or r.get("display_name") or "", authors, int(year) if year else None,
                        _norm_doi(r.get("doi") or "")))
    return out


def _s2(data: dict) -> list[_Hit]:
    return [_Hit(r.get("title") or "", [a.get("name") or "" for a in r.get("authors") or []],
                 int(r["year"]) if r.get("year") else None,
                 _norm_doi((r.get("externalIds") or {}).get("DOI") or "")) for r in data.get("data") or []]


def _crossref_work(data: dict) -> _Hit | None:
    message = data.get("message")
    return _crossref_item(message) if isinstance(message, dict) else None


def _datacite_work(data: dict) -> _Hit | None:
    """DataCite JSON:API record: data.attributes.titles[0].title, creators[].familyName or name, publicationYear."""
    attrs = (data.get("data") or {}).get("attributes")
    if not isinstance(attrs, dict):
        return None
    titles = attrs.get("titles") or []
    title = (titles[0] or {}).get("title") or "" if titles else ""
    authors = []
    for c in attrs.get("creators") or []:
        family = c.get("familyName") or ""
        if family:
            authors.append(" ".join(p for p in (c.get("givenName") or "", family) if p))
        else:
            authors.append(c.get("name") or "")
    year = attrs.get("publicationYear")
    return _Hit(title, authors, int(year) if year else None, _norm_doi(attrs.get("doi") or ""))


# ---------------------------------------------------------------- matching

def _judge(entry: Entry, hit: _Hit) -> tuple[float, list[str], str]:
    """Title ratio, list of author/year problems, and an evidence string.

    Author and year are checked only when both the entry and the hit carry them."""
    ratio, title_problem = _compare_titles(entry.fields.get("title", ""), hit.title)
    problems = [title_problem] if title_problem else []
    fam = first_family(entry.fields.get("author", ""))
    if fam and hit.authors and f" {fam} " not in f" {_plain(' '.join(hit.authors))} ":
        problems.append(f"author {fam!r} not in {', '.join(hit.authors[:3])}")
    year = _year(entry.fields.get("year") or entry.fields.get("date", ""))
    if year is not None and hit.year is not None and abs(int(hit.year) - year) > 1:
        problems.append(f"year {year} vs {hit.year}")
    evidence = f"title {ratio:.2f} vs {hit.title!r}"
    if problems:
        evidence += "; " + "; ".join(problems)
    return ratio, problems, evidence


def grey_marker(entry: Entry) -> str:
    """Why the entry looks like grey literature (R168), or "" when nothing marks it."""
    etype = entry.type.lower()
    if etype in GREY_TYPES:
        return f"type {etype}"
    for name in GREY_FIELDS:
        m = GREY_WORDS_RE.search(entry.fields.get(name, ""))
        if m:
            return f"{name} says {m.group(0)!r}"
    for name in GREY_PUBLISHER_FIELDS:
        m = GREY_PUBLISHER_RE.search(entry.fields.get(name, ""))
        if m:
            return f"{name} {m.group(0)!r}"
    if etype in PROCEEDINGS_TYPES and not entry.fields.get("doi", "").strip() \
            and not entry.fields.get("isbn", "").strip():
        return f"type {etype} with neither DOI nor ISBN"
    return ""


def _failed(status: int) -> bool:
    """Source-level failure: network error, rate limit, server error or other non-200 except 404."""
    return status != 200 and status != 404


def _with(url: str, params: dict) -> str:
    params = {k: v for k, v in params.items() if v}
    return url + ("?" + urlencode(params, quote_via=quote) if params else "")


SOURCES = ("crossref", "openalex", "semantic_scholar")
_PARSERS = {"crossref": _crossref_search, "openalex": _openalex, "semantic_scholar": _s2}


def _search_request(name: str, title: str, mailto: str, keys: dict) -> tuple[str, dict]:
    if name == "crossref":
        return _with("https://api.crossref.org/works", {"query.bibliographic": title, "rows": "3", "mailto": mailto}), {}
    if name == "openalex":
        return _with("https://api.openalex.org/works", {"search": title, "per-page": "3",
                                                        "api_key": keys.get("openalex", ""), "mailto": mailto}), {}
    headers = {"x-api-key": keys["semantic_scholar"]} if keys.get("semantic_scholar") else {}
    return _with("https://api.semanticscholar.org/graph/v1/paper/search",
                 {"query": title, "limit": "3", "fields": "title,authors,year,externalIds"}), headers


class _Incomplete(Exception):
    """A cached record lacks a fact the judgement now needs; fall back to the network."""


class _Facts:
    """Raw API facts (hits or not-found or failed), fetched live and recorded, or replayed from a cache record.

    Record shape: {"doi": {"failed": bool, "hit": hit-dict | None},
                   "datacite": {"failed": bool, "hit": hit-dict | None}   (only after a Crossref 404),
                   "search": {source: {"failed": bool, "hits": [hit-dict, ...]}}}."""

    def __init__(self, record: dict, *, fetch: Fetch | None = None, mailto: str = "", keys: dict | None = None):
        self.record, self.fetch, self.mailto, self.keys = record, fetch, mailto, keys or {}

    def _get(self, url: str, headers: dict, parse: Callable[[dict], object]) -> tuple[bool, object]:
        """(failed, parsed). A 404 is an answer (not found); a 200 with an empty body, a body that is not
        a JSON object, or one whose shape the parser cannot read counts as the source not answering."""
        status, body = self.fetch(url, headers)
        if _failed(status):
            return True, None
        if status == 404:
            return False, None
        if not body or not body.strip():
            return True, None
        try:
            data = json.loads(body)
            parsed = parse(data) if isinstance(data, dict) else None
        except Exception:
            return True, None  # not JSON or an unexpected shape: the source counts as failing
        return (True, None) if parsed is None else (False, parsed)

    def doi(self, doi: str) -> tuple[bool, _Hit | None]:
        if self.fetch is None:
            fact = self.record.get("doi")
            if not isinstance(fact, dict):
                raise _Incomplete("doi")
            return bool(fact["failed"]), _Hit(**fact["hit"]) if fact.get("hit") else None
        url = _with("https://api.crossref.org/works/" + quote(doi, safe="/"), {"mailto": self.mailto})
        failed, hit = self._get(url, {}, _crossref_work)
        self.record["doi"] = {"failed": failed, "hit": asdict(hit) if hit else None}
        return failed, hit

    def datacite(self, doi: str) -> tuple[bool, _Hit | None]:
        if self.fetch is None:
            fact = self.record.get("datacite")
            if not isinstance(fact, dict):
                raise _Incomplete("datacite")
            return bool(fact["failed"]), _Hit(**fact["hit"]) if fact.get("hit") else None
        url = "https://api.datacite.org/dois/" + quote(doi, safe="/")
        failed, hit = self._get(url, {}, _datacite_work)
        self.record["datacite"] = {"failed": failed, "hit": asdict(hit) if hit else None}
        return failed, hit

    def search(self, name: str, title: str) -> tuple[bool, list[_Hit]]:
        if self.fetch is None:
            fact = (self.record.get("search") or {}).get(name)
            if not isinstance(fact, dict):
                raise _Incomplete(name)
            return bool(fact["failed"]), [_Hit(**h) for h in fact.get("hits") or []]
        url, headers = _search_request(name, title, self.mailto, self.keys)
        failed, hits = self._get(url, headers, _PARSERS[name])
        hits = hits or []
        self.record.setdefault("search", {})[name] = {"failed": failed, "hits": [asdict(h) for h in hits]}
        return failed, hits


def _title_search(entry: Entry, facts: _Facts, *, doi_dead: bool = False) -> LookupResult:
    """Title search on every source in turn. With no match, the entry is decided (missing for strict types)
    when doi_dead (Crossref and DataCite both 404) and at least one source answered (all three for a thesis,
    R165), or when all three sources answered and no grey-literature marker applies (R168)."""
    title = query_title(entry.fields.get("title", ""))
    failures, best = 0, None
    answered: set[str] = set()
    for name in SOURCES:
        failed, hits = facts.search(name, title)
        if failed:
            failures += 1
            continue
        answered.add(name)
        judged = sorted((_judge(entry, h) + (h,) for h in hits), key=lambda t: t[0], reverse=True)
        if judged and judged[0][0] >= TITLE_MATCH:
            ratio, problems, evidence, hit = judged[0]
            return LookupResult(entry.key, "partial" if problems else "verified", name, evidence, hit.doi)
        if judged and (best is None or judged[0][0] > best[0]):
            best = (judged[0][0], name, judged[0][2])
    if failures == len(SOURCES):
        return LookupResult(entry.key, "unreachable", "", "every source failed (network, rate limit or server error)")
    evidence = "no title match on any reachable source"
    if failures:
        evidence += f" ({failures} of {len(SOURCES)} sources did not answer)"
    if best:
        evidence += f"; closest {best[1]}: {best[2]}"
    all_answered = answered == set(SOURCES)
    grey = grey_marker(entry)
    if doi_dead:
        decided = all_answered if entry.type.lower() in ALL_SOURCES_TYPES else bool(answered)
    else:
        decided = all_answered and not grey
    if grey and not decided:
        evidence += f"; grey literature ({grey})"
    return _not_found(entry, evidence, decided=decided)


def _not_found(entry: Entry, evidence: str, *, decided: bool) -> LookupResult:
    """R94 as amended by D13 and R168: missing only when the lookup is decided (see _title_search) and the entry
    type is one indexes cover; else not_indexed."""
    if decided and entry.type.lower() in STRICT_TYPES:
        return LookupResult(entry.key, "missing", "", evidence)
    return LookupResult(entry.key, "not_indexed", "",
                        f"not found in citation indexes (type {entry.type.lower()}); {evidence}")


def _judge_doi(entry: Entry, doi: str, hit: _Hit, source: str) -> LookupResult:
    if not entry.fields.get("title"):
        return LookupResult(entry.key, "partial", source, f"DOI resolves to {hit.title!r}; entry has no title",
                            hit.doi or doi)
    if not norm_title(hit.title):
        return LookupResult(entry.key, "partial", source, "DOI resolves but the record has no title", hit.doi or doi)
    ratio, problems, evidence = _judge(entry, hit)
    if ratio < TITLE_MISMATCH:
        status = "mismatch"
    elif ratio >= TITLE_MATCH and not problems:
        status = "verified"
    else:
        status = "partial"
    return LookupResult(entry.key, status, source, evidence, hit.doi or doi)


def _doi_lookup(entry: Entry, doi: str, facts: _Facts) -> LookupResult:
    failed, hit = facts.doi(doi)
    if not failed and hit is not None:
        return _judge_doi(entry, doi, hit, "crossref")
    reason = "Crossref unreachable for DOI"
    if not failed:
        # Crossref 404: DataCite registers arXiv, Zenodo and many dataset DOIs (R93).
        dc_failed, dc_hit = facts.datacite(doi)
        if not dc_failed and dc_hit is not None:
            return _judge_doi(entry, doi, dc_hit, "datacite")
        failed = dc_failed
        reason = "DOI not found on Crossref; DataCite unreachable for DOI" if dc_failed \
            else "DOI not found on Crossref or DataCite"
    # DOI not found or unavailable: fall back to a title search.
    if not entry.fields.get("title"):
        if failed:
            return LookupResult(entry.key, "unreachable", "", f"{reason}; entry has no title", doi)
        res = _not_found(entry, f"{reason}; entry has no title", decided=False)
        res.doi = doi
        return res
    res = _title_search(entry, facts, doi_dead=not failed)
    if res.status in ("verified", "partial") and not failed:
        res.status = "partial"  # the work exists, but the DOI in the entry does not resolve
        res.doi_unresolved = True
    res.evidence = f"{reason} {doi}; {res.evidence}"
    res.doi = res.doi or doi
    return res


def _resolve(entry: Entry, facts: _Facts) -> LookupResult:
    doi = _norm_doi(entry.fields.get("doi", ""))
    return _doi_lookup(entry, doi, facts) if doi else _title_search(entry, facts)


# ---------------------------------------------------------------- cache

def cache_key(entry: Entry) -> str:
    doi = _norm_doi(entry.fields.get("doi", ""))
    if doi:
        return "doi:" + doi
    title = norm_title(entry.fields.get("title", ""))
    return "title:" + title if title else ""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _fresh(record: dict) -> bool:
    try:
        checked = datetime.fromisoformat(record["checked_at"])
    except (KeyError, TypeError, ValueError):
        return False
    if checked.tzinfo is None:
        checked = checked.replace(tzinfo=timezone.utc)
    return _now() - checked <= CACHE_MAX_AGE


def _cached(entry: Entry, cache: dict) -> LookupResult | None:
    """Judge ``entry`` afresh against the cached raw facts; None when absent, stale, incomplete or unreadable."""
    record = cache.get(cache_key(entry))
    if not isinstance(record, dict) or not _fresh(record):
        return None
    try:
        res = _resolve(entry, _Facts(record))
    except Exception:  # _Incomplete, an old-format record, or a hand-edited one
        return None
    return None if res.status in NOT_CACHED else res


def load_cache(path: Path) -> dict:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save_cache(path: Path, cache: dict) -> None:
    """Atomic write: temp file in the same directory, then os.replace."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".cite_lookup.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(cache, fh, indent=1, sort_keys=True)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def default_cache_path() -> Path:
    data = os.environ.get("CLAUDE_PLUGIN_DATA")
    if data:
        return Path(data) / "cache" / "cite_lookup.json"
    return Path.cwd() / ".ploma" / "cite_lookup.json"


# ---------------------------------------------------------------- public API

def user_agent(mailto: str = "") -> str:
    return f"{USER_AGENT} (mailto:{mailto})" if mailto else USER_AGENT


def default_fetch(url: str, headers: dict) -> tuple[int, str]:
    """GET ``url`` with a 10 s timeout; (status, body). Network errors and timeouts give (0, ""); never raises."""
    hdrs = {"User-Agent": user_agent(), "Accept": "application/json"}
    hdrs.update(headers or {})
    try:
        req = urllib.request.Request(url, headers=hdrs)
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            body = ""
        return exc.code, body
    except Exception:
        return 0, ""


def lookup(entry: Entry, *, fetch: Fetch, mailto: str = "", keys: dict | None = None, cache: dict) -> LookupResult:
    """Existence check for one entry. Raw API facts are cached; the verdict is re-judged against the entry on every read."""
    ckey = cache_key(entry)
    if not ckey:
        return LookupResult(entry.key, "skipped", "", "entry has neither DOI nor title")
    hit = _cached(entry, cache)
    if hit is not None:
        return hit
    record: dict = {}
    res = _resolve(entry, _Facts(record, fetch=fetch, mailto=mailto, keys=keys))
    source_failed = any(isinstance(f, dict) and f.get("failed") for f in (record.get("search") or {}).values())
    if res.status not in NOT_CACHED and not (res.status == "not_indexed" and source_failed):
        record["checked_at"] = _now().isoformat()
        cache[ckey] = record
    return res


def _throttled(fetch: Fetch, delay_s: float) -> Fetch:
    state = {"called": False}

    def wrapped(url: str, headers: dict) -> tuple[int, str]:
        if state["called"] and delay_s > 0:
            time.sleep(delay_s)
        state["called"] = True
        return fetch(url, headers)
    return wrapped


def run(entries: list[Entry], *, max_lookups: int, delay_s: float = 0.5, cache_path: Path, mailto: str = "",
        keys: dict | None = None, fetch: Fetch | None = None, time_budget_s: float = TIME_BUDGET_S,
        clock: Callable[[], float] = time.monotonic) -> list[LookupResult]:
    """Look up every entry. Cache hits are free; at most ``max_lookups`` entries go to the network, the rest are
    skipped. Once ``time_budget_s`` seconds (measured by ``clock``) have passed, entries that would need the network
    are skipped with "time budget reached". The cache is saved every SAVE_EVERY network lookups and at the end."""
    keys = keys or {}
    if fetch is None:
        ua = user_agent(mailto)

        def fetch(url: str, headers: dict) -> tuple[int, str]:
            # default_fetch is looked up at call time so tests can replace it.
            return default_fetch(url, {"User-Agent": ua, **headers})
    net = _throttled(fetch, delay_s)
    cache = load_cache(cache_path)
    results, used, saved_at = [], 0, 0
    started = clock()
    for entry in entries:
        if cache_key(entry) and _cached(entry, cache) is None:
            if used >= max_lookups:
                results.append(LookupResult(entry.key, "skipped", "", f"over the lookup cap of {max_lookups} per run"))
                continue
            if clock() - started >= time_budget_s:
                results.append(LookupResult(entry.key, "skipped", "", "time budget reached"))
                continue
            used += 1
        try:
            results.append(lookup(entry, fetch=net, mailto=mailto, keys=keys, cache=cache))
        except Exception as exc:  # one bad entry must not abort the run or lose the cache
            results.append(LookupResult(entry.key, "unreachable", "", f"lookup error: {exc!r}"))
        if used - saved_at >= SAVE_EVERY:
            save_cache(cache_path, cache)
            saved_at = used
    save_cache(cache_path, cache)
    return results


def _table(results: list[LookupResult]) -> str:
    rows = [("key", "status", "source")] + [(r.key, r.status, r.source or "-") for r in results]
    widths = [max(len(row[i]) for row in rows) for i in range(3)]
    return "\n".join("  ".join(c.ljust(w) for c, w in zip(row, widths)).rstrip() for row in rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check that bibliography entries exist (Crossref, OpenAlex, Semantic Scholar).")
    parser.add_argument("bib", help="BibTeX file")
    parser.add_argument("--keys", default="", help="comma-separated entry keys to check (default: all)")
    parser.add_argument("--max", type=int, default=50, help="network lookups per run (default 50)")
    parser.add_argument("--mailto", default="", help="contact address for the Crossref and OpenAlex polite pools")
    parser.add_argument("--openalex-key", default=os.environ.get("OPENALEX_API_KEY", ""), help="OpenAlex API key")
    parser.add_argument("--s2-key", default=os.environ.get("SEMANTIC_SCHOLAR_API_KEY", ""),
                        help="Semantic Scholar API key")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 0 if exc.code == 0 else 2
    try:
        text = Path(args.bib).read_text(encoding="utf-8", errors="replace")
    except OSError:
        msg = f"cannot read bib file {args.bib}"
        print(json.dumps({"error": msg}) if args.json else f"cite_lookup: {msg}", file=sys.stdout if args.json else sys.stderr)
        return 2
    entries = parse_bib(text)
    wanted = {k.strip() for k in args.keys.split(",") if k.strip()}
    if wanted:
        entries = [e for e in entries if e.key in wanted]
    keys = {k: v for k, v in (("openalex", args.openalex_key), ("semantic_scholar", args.s2_key)) if v}
    results = run(entries, max_lookups=args.max, cache_path=default_cache_path(), mailto=args.mailto, keys=keys)
    if args.json:
        print(json.dumps({"results": [r.to_dict() for r in results]}, indent=2))
    else:
        print(_table(results) if results else "cite_lookup: no entries")
    return 1 if any(r.status in ("missing", "mismatch") for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
