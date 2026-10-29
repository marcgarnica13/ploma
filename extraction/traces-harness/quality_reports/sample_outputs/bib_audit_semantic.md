# Bibliography Semantic Audit

**Date:** 2026-06-04 (full-audit refresh; supersedes the Phase-1 run, which DOI-verified the 9 new refs)
**Bibliography:** manuscript/mybib.bib (64 entries)
**Files scanned:** manuscript/samplepaper.tex (33 unique cited keys, uncommented)

## Summary

| Check | Critical | Medium | Low |
|---|---|---|---|
| Structural (missing / typos) | 0 | 0 | 0 |
| Citation drift (duplicates) | 0 | 0 | 0 (3 flags, all false positives) |
| DOI verification | 0 | 0 | 8 entries without DOI (optional) |
| Style consistency | 0 | 0 | 0 (`\cite` only) |
| Unused entries | — | — | 31 (informational) |

**Verdict: PASS.** No missing citations, no typos/case mismatches, no real duplicates, citation
style consistent. Bibliography is submission-clean.

## Structural

- **Missing entries (cited, absent from .bib): NONE** — all 33 cited keys resolve (consistent with the
  clean `make` build). The earlier `Fernandeznavarro2016` vs `FernandezNavarro2016` case mismatch is
  gone (that citation was removed; the entry is now merely unused).
- **Typo/case candidates: NONE.**
- **Unused entries: 31** (in `.bib`, never cited) — leftovers from earlier drafts (e.g.,
  `Pappalardo2019`/`Pappalardo2020` from the retired Wyscout data, `Mannila1997`, `Rein2016`,
  `Tenga2003`, `Bialkowski2014a`, several PM entries). Harmless — `splncs04` prints only cited works.
  *Optional tidy-up:* prune them for a cleaner `.bib`, but not required.

## Citation drift (semantic)

- **Duplicate DOIs: none.**
- **Duplicate titles: 3 pairs flagged, ALL FALSE POSITIVES** (parser collided on shared
  `booktitle`/brace fields; manually confirmed distinct papers):
  - `Bergami2021` ("Aligning Data-Aware Declarative Process Models…") ≠ `Guenther2007` ("Fuzzy Mining…").
  - `Leoni2022` ("Foundations of Process Enhancement") ≠ `Leemans2015` ("Discovery of Frequent Episodes…").
  - `Bialkowski2014` (ICDM, "Large-Scale Analysis of Soccer Matches…") ≠ `Bialkowski2014a` (ICDM
    **Workshop**, "Identifying Team Style in Soccer…") — same authors/year, genuinely different papers.
  → No action needed.

## DOI verification

- **25 of 33 cited entries carry a DOI.** The 8 without one are LOW severity (DOI is optional):
  `Clijmans2022`, `Davis202207`, `Dijkman2011`, `Gyarmati2014`, `Kulakli2021`, `Sivaraman2002`,
  `StatsBomb2023` (open-data `@Misc`, no DOI — correct), `Weijters2006` (Heuristic-Miner tech report).
- The 9 newly added 2023–2026 references (TacticAI/`Wang2024`, GoalNet/`Jiang2025`, `Demir2025`,
  `Chan2025`, `McCarthy2023`, …) had their DOIs verified against Crossref / Semantic Scholar /
  OpenAlex during Phase 1 of this revision — all PASSed. No re-verification needed this round.

## Style consistency

- LLNCS + `splncs04.bst`: the manuscript uses `\cite{…}` exclusively (no `\citep`/`\citet` mix). PASS.

## Next steps (optional)

1. (Optional) Prune the 31 unused entries for a tidier `.bib`.
2. No required fixes — bibliography is submission-clean.
