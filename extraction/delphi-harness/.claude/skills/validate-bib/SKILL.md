---
name: validate-bib
description: Validate bibliography entries against citations in the proposal. Structural checks (missing/unused entries, malformed fields) by default; `--semantic` adds citation-drift detection, DOI verification (Crossref / Semantic Scholar / OpenAlex — all free, no API key), and style-consistency checks.
argument-hint: "[--semantic] [--skip-doi] [--cite-claim]"
allowed-tools: ["Read", "Grep", "Glob", "Write", "Bash", "WebFetch"]
---

# Validate Bibliography

Cross-reference citations in the proposal against bibliography entries. Two modes:

- **Default (structural):** missing entries, unused entries, malformed fields, typo candidates.
- **`--semantic`:** adds citation-drift detection (duplicate entries for the same paper), DOI verification, and citation-style consistency within each file.

**All citation-verification APIs used here are free and require NO API key** — Crossref
(`api.crossref.org`), Semantic Scholar (`api.semanticscholar.org`), and OpenAlex (`api.openalex.org`).

Report saved to `quality_reports/bib_audit_[structural|semantic].md`.

## Mode 1: Structural (default)

### Steps

1. **Read the bibliography file** and extract all citation keys.

2. **Scan the proposal `.tex` files for citation keys:**
   - `.tex`: `\cite{`, `\citet{`, `\citep{`, `\citeauthor{`, `\citeyear{`, `\textcite{`, `\parencite{`
     (handle comma-separated multi-keys).
   - Extract all unique citation keys used.

3. **Cross-reference:**
   - **Missing entries (CRITICAL):** cited in the proposal, absent from `.bib`.
   - **Unused entries (informational):** in `.bib` but never cited.
   - **Typo candidates:** keys within edit-distance 2 of a `.bib` key (e.g., `Smith2020` vs `Smth2020`).

4. **Check entry quality:**
   - Required fields present (author, title, year, journal/booktitle).
   - Author field properly formatted.
   - Year in 1900–current.
   - No malformed characters / encoding issues.
   - `doi` field normalized (no leading `https://doi.org/`).

5. **Write report** to `quality_reports/bib_audit_structural.md`.

### Files scanned

```
proposal/proposal_a4.tex
proposal/proposal_slides.tex
proposal/*.tex             # any other proposal TeX sources
```

### Bibliography location

`proposal/refs.bib`.

## Mode 2: Semantic (`--semantic`)

Everything in Mode 1, plus:

### 2a. Citation drift detection

Multiple `.bib` entries describing the same paper under different keys. Symptoms:

- `Smith2020` + `Smith2020a` with identical DOI or title.
- `vanderAalst2016` + `Aalst2016` both pointing to the same paper.
- Collaborator-merged `.bib` files.

**Detection heuristics (any → FLAG):**

| Check | Signal |
|---|---|
| Same DOI across keys | Hard-duplicate (CRITICAL) |
| Same title (case-insensitive, punct-stripped) | Likely duplicate (CRITICAL) |
| Same author+year+journal | Probable duplicate (MEDIUM) |
| Title Jaccard > 0.85 on tokens ≥ 4 chars | Soft-duplicate (LOW) |

For each flagged pair: list both keys, where each is cited, and recommend a canonical key (prefer most-cited, then alphabetically first).

### 2b. DOI / metadata verification (optional; network — all free, no API key)

For each entry, verify metadata against one or more **free, keyless** endpoints:

- **Crossref** — `https://api.crossref.org/works/{doi}` (primary, when a `doi` is present).
- **Semantic Scholar** — `https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}?fields=title,authors,year,venue`
  (also accepts arXiv ids via `arXiv:{id}`; good fallback for preprints).
- **OpenAlex** — `https://api.openalex.org/works/doi:{doi}` (broad coverage; useful when an entry has
  no DOI — search by title via `https://api.openalex.org/works?search={title}`).

None of these require an API key or token. (Crossref and OpenAlex appreciate a `mailto=` query param
for the "polite pool"; it is optional.) Compare:

- First-author last name
- Year
- Title (Jaccard > 0.7 on normalized tokens)
- Container-title / venue / journal (exact or abbreviation)

**Severity:**

- Author or title mismatch → CRITICAL (wrong paper)
- Year mismatch → MEDIUM (preprint vs published, or typo)
- Journal/venue mismatch → LOW (legitimate preprint variants — common for arXiv→conference)

**Rate limit:** cap 50 lookups per run, 0.5s delay between calls. Cache in `quality_reports/.doi_cache.json`.

**Opt-out:** `--skip-doi` for offline or no-WebFetch environments.

### 2c. Style consistency within each file

For each file, count citation commands (`\cite` vs `\citep` vs `\citet`). FLAG files with mixed styles without an obvious pattern (e.g., 20× `\cite` and 3× `\citep` in the same document). Low-severity.

### 2d. Cite-claim sanity (flag-only)

Gated behind `--cite-claim`. For the top-10 most-cited works per file, WebFetch the crossref abstract and surface it beside the in-text context. **No auto-judgment** — humans decide if the claim matches.

### Report structure (`quality_reports/bib_audit_semantic.md`)

```markdown
# Bibliography Semantic Audit

**Date:** YYYY-MM-DD
**Bibliography:** proposal/refs.bib (N entries)
**Files scanned:** [list]

## Summary

| Check | Critical | Medium | Low |
|---|---|---|---|
| Structural | | | |
| Citation drift | | | |
| DOI verification | | | |
| Style consistency | 0 | 0 | |

## Critical Issues

### Duplicate entries
| Keys | Signal | Citations | Recommended canonical |
|---|---|---|---|

### DOI mismatches
| Key | Field | .bib value | crossref value |
|---|---|---|---|

## Medium / Low issues
…

## Next steps
1. Resolve duplicates — pick canonical key, update citations, remove orphans.
2. Fix DOI mismatches — verify paper in crossref or strip the wrong DOI.
3. Review style-consistency notes.
```

## Exit behavior

- **Structural:** exit 0; report enumerates issues.
- **Semantic:** exit 0 if only LOW findings; exit 1 on any CRITICAL. Usable as a pre-submission gate.

## Cross-references

- `.claude/skills/review-proposal/SKILL.md` — pair for full pre-submission.

## What this skill does NOT do

- Judge whether a citation is used in the right *context* (`--cite-claim` surfaces abstracts but does not judge).
- Auto-fix your `.bib` file — all edits are recommendations.
- Check non-DOI identifiers (ISBN, arXiv, SSRN) — roadmap.
