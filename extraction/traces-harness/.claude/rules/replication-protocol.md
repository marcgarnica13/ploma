---
paths:
  - "src/**/*.py"
  - "src/sports_pm/**/*.py"
---

# Replication-First Protocol

**Core principle:** Reproduce the manuscript's reported numbers/figures from the pipeline BEFORE extending or refactoring.

This project is a Python + MongoDB pipeline (Python 3.12, uv-managed; pm4py 2.7.22.4 / pandas 3.0.3 /
numpy 2.4.6). There is no test suite, so a deliberate reproduce-then-extend discipline is the safety net.

---

## Phase 1: Inventory & Baseline

Before changing any pipeline code:

- [ ] Read `CLAUDE.md` (pipeline architecture) and the manuscript's methods/results sections.
- [ ] Inventory the run: which script (`parse_soccerlogs_matches.py` / `parse_statsbomb_matches.py`),
      which Mongo database (`staging_soccerlogs` / `statsbomb_lake`), which result dir under
      `src/results/`.
- [ ] Confirm the environment contract is satisfiable: `MONGO_USER`, `MONGO_PWD`, `MONGO_STR`,
      `TAGS_FILE`, `RESULTS_FILE` set (`STATSBOMB_DATA_DIR` for the StatsBomb-JSON source); deps
      installed via `uv sync` from the **pinned** `src/pyproject.toml` + `src/uv.lock`.
- [ ] Record the gold-standard numbers/figures from the manuscript:

```markdown
## Reproduction Targets: samplepaper.tex

| Target | Table/Figure | Value | Notes |
|--------|-------------|-------|-------|
| Avg fitness (offensive net) | Table 1 / Fig 3 | 0.81 | dependency threshold 0.9, StatsBomb source |
| # offensive possessions kept | text §4 | 12,430 | after filter_offensive_sequences |
```

- [ ] Store targets in `quality_reports/reproduction_targets.md`.

---

## Phase 2: Reproduce & Execute

- [ ] Follow [`python-code-conventions.md`](python-code-conventions.md) for all coding standards.
- [ ] **Run from `src/`** so `sports_pm` and the env-var paths resolve.
- [ ] Do not "improve" the pipeline during reproduction — match the existing configuration exactly
      (data source, possession-segmentation rule, offensive filter, 24-zone grid, dependency threshold,
      fitness objective).
- [ ] Preserve the documented invariants: the `action##zone` activity-key format, the case id
      `possession_count = "{match_id}_{team_id}_{seq_index}"`, and coordinate orientation.
- [ ] Capture outputs into a timestamped result dir under `src/results/` (do not overwrite a prior
      run's dir).

---

## Phase 3: Verify Match

### Tolerance Thresholds

| Type | Tolerance | Rationale |
|------|-----------|-----------|
| Integers (N possessions, match/case counts) | Exact match | No reason for any difference if the data slice is fixed |
| Fitness / metric point values | < 0.01 | Display rounding in the paper |
| Generalization / aggregate scores | < 0.02 | Minor variation across pm4py internals |
| Percentages / shares | < 0.1pp | Display rounding |

> **MongoDB reproducibility caveat.** Exact reproduction depends on the same Mongo data being
> available. A different data snapshot (or no Mongo access at all) makes integer counts diverge — this
> is a data-availability issue, not a code defect. Document the data snapshot used.

### If Mismatch

**Do NOT proceed to extensions.** Isolate which stage introduces the difference (segmentation →
offensive filter → standardization → discovery → fitness), check common causes (different Mongo
snapshot, unpinned dependency version, a changed activity-key format, a coordinate flip, an unseeded
stochastic step), and document the investigation even if unresolved.

### Reproduction Report

Save to `quality_reports/reproduction_report.md`:

```markdown
# Reproduction Report: samplepaper.tex
**Date:** [YYYY-MM-DD]
**Script:** [parse_statsbomb_matches.py / parse_soccerlogs_matches.py]
**Data source:** [statsbomb_lake / staging_soccerlogs] — snapshot: [date/desc]

## Summary
- **Targets checked / Passed / Failed:** N / M / K
- **Overall:** [REPRODUCED / PARTIAL / FAILED]

## Results Comparison

| Target | Paper | Ours | Diff | Status |
|--------|-------|------|------|--------|

## Discrepancies (if any)
- **Target:** X | **Investigation:** ... | **Resolution:** ...

## Environment
- Python version, key package versions (pinned in src/pyproject.toml + uv.lock), data source
  (Mongo database + snapshot, or STATSBOMB_DATA_DIR JSON tree), env vars set, result dir produced.
```

---

## Phase 4: Only Then Extend

After reproduction is verified (all targets PASS):

- [ ] Commit the reproduced baseline: "Reproduce paper Table/Fig X — targets match".
- [ ] Now extend (new event types, different zone granularity, alternative discovery, new figures).
- [ ] Each extension builds on the verified baseline.

---

## Enforcement

This rule is enforced by the [`/audit-reproducibility`](../skills/audit-reproducibility/SKILL.md) skill. It parses numeric claims from the manuscript, locates matching values in the pipeline outputs (`src/results/...` or the user-specified outputs directory), and compares against the tolerance thresholds above. Run it:

- **Before submission** — `/audit-reproducibility manuscript/samplepaper.tex`
- **Before releasing the code/data package** — same invocation; aim for zero FAILs.
- **As a pre-commit gate** — wire into `/commit` when the diff touches both the manuscript and pipeline code.

The skill exits 1 on any tolerance violation, so it integrates cleanly with quality gates.

---

## Claims Provenance: `passport.yaml`

A passport is a single per-paper, per-branch YAML file at `quality_reports/passports/<paper-slug>.yaml` that records, for each verified numeric claim in the manuscript, the script invocation and output file that produced it. The contract is intentionally narrow: numeric claims only (fitness/metric values, possession/case counts, percentages from tables/figures), not prose claims (which `/verify-claims` handles separately).

Create one passport per paper under `quality_reports/passports/`.

### Schema

```yaml
paper:
  slug: <paper-slug>                              # used in filename + report headings
  title: <full paper title>
  branch: <git branch on which this passport is current>
  last_audit: <ISO-8601 timestamp>
  last_audit_by: "/audit-reproducibility"         # or human, or another skill

claims:
  - id: C1                                        # stable identifier (used in cross-references)
    claim: "avg fitness = 0.81 (dependency 0.9, N=12430 possessions)"  # text/paraphrase from manuscript
    location: "samplepaper.tex:Table 1"           # where it appears in the paper
    source_file: src/notebooks/discovery/parse_statsbomb_matches.py   # script that produced the value
    source_line: 88                               # nearest line in the script
    output_file: src/results/offensive_statsbomb_pass_09x/metrics.json # where the value lives on disk
    output_field: avg_fitness                      # field within the output (e.g., dict key, column)
    tolerance:
      point_estimate: 0.01                         # absolute tolerance per Phase 3 above
      n: exact
    last_verified_on: <ISO-8601>
    last_verified_by: "/audit-reproducibility"
    status: PASS                                   # PASS | FAIL | STALE | UNVERIFIED
    notes: |
      Optional notes — e.g., "matches paper to 2 decimals; count exact for the
      documented Mongo snapshot."
```

### `status` semantics

- **PASS** — last audit confirmed the claim within tolerance.
- **FAIL** — last audit detected a discrepancy outside tolerance. Blocks `/commit` for the affected files unless explicit override.
- **STALE** — the underlying `source_file` or `output_file` was modified after `last_verified_on`. Re-run `/audit-reproducibility` to refresh.
- **UNVERIFIED** — the claim was added to the manuscript but never run through `/audit-reproducibility`. Should not appear in a submission-ready passport.

### Integration

- **`/audit-reproducibility`** reads the passport at start, writes back after every claim audit. Failed claims are reported with their `id` and `location` so the author can find them in the manuscript instantly.
- **`/commit`** reads the passport when a diff touches both `manuscript/samplepaper.tex` and any `source_file` listed. If the passport contains any FAIL or STALE for a claim whose `source_file` is in the diff, `/commit` halts (advisory by default; gate-refuse if `--strict-passport` is set in `.claude/settings.json`).
- **`/review-paper`** (default mode + `--peer`) appends a summary section to its report when the passport exists: `claims: N total, PASS: A, FAIL: B, STALE: C, UNVERIFIED: D`. Editors and referees know whether numeric claims have been independently verified at draft time.

### Inspiration

The pattern is borrowed from [Imbad0202/academic-research-skills](https://github.com/Imbad0202/academic-research-skills)'s "Material Passport" concept (a YAML state-file threaded through their pipeline). Their schema is heavier (13 contracts, threaded through ~6 agents); ours is deliberately scoped to numeric-claim provenance only. Forkers who need broader provenance tracking can extend the schema or vendor ARS's design directly.

### Anti-patterns

- **Do not auto-populate** the passport at `/audit-reproducibility` time without showing the user the inferred mapping. Source-line inference is best-effort; the author confirms.
- **Do not promote UNVERIFIED claims to PASS** without running the actual numeric audit. The passport is a verified-state artifact; bypassing the verification defeats the purpose.
- **Do not use the passport as a substitute for `/verify-claims`.** The passport handles numeric claims with code provenance; `/verify-claims` handles citation and named-entity claims with literature provenance. Both run.
