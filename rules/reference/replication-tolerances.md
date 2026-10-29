# Replication first and numeric tolerances

Applies when `pipeline.enabled` is true. Reproduce the manuscript's reported numbers from the pipeline before extending or refactoring it.

## Phase 1: inventory and baseline

- Read the manuscript's method and results sections and the project's `CLAUDE.md`.
- Identify the run: the script and command (`pipeline.rerun`, run from `pipeline.run_from`) and the results directory (`pipeline.outputs_dir`).
- Confirm the environment contract: every variable in `pipeline.env_contract` is set and dependencies are installed from the pinned lock file.
- Record the targets in `<outputs.dir>/reproduction_targets.md`:

```markdown
| Target | Table or figure | Value | Notes |
|---|---|---|---|
```

## Phase 2: reproduce

- Run from `pipeline.run_from`.
- Do not improve the pipeline while reproducing. Match the existing configuration exactly.
- Respect every invariant in `pipeline.gotchas`.
- Write outputs to a new timestamped directory; never overwrite a previous run.

## Phase 3: verify the match

Tolerances come from `pipeline.tolerances` (defaults in the eager limits rule):

| Kind | Key | Default | Rationale |
|---|---|---|---|
| Counts | `counts` | exact | a fixed data slice gives identical integers |
| Point metrics | `metrics` | 0.01 | display rounding |
| Aggregates | `aggregates` | 0.02 | small numerical variation |
| Percentages | `percentages_pp` | 0.1 pp | display rounding |

A different data snapshot makes counts diverge. That is a data availability issue, not a code defect; record the snapshot used.

If a target misses: do not extend. Isolate the stage that introduces the difference, check the usual causes (data snapshot, unpinned dependency, changed key format, unseeded randomness) and document the investigation even when unresolved.

Save `<outputs.dir>/reproduction_report.md` with the date, script, data source, a targets table (paper, ours, difference, status), discrepancies and the environment.

## Phase 4: only then extend

Commit the reproduced baseline first. Each extension builds on the verified baseline.

## Enforcement

`/ploma:audit-reproducibility` parses numeric claims, finds the matching values under `pipeline.outputs_dir` (keys in `pipeline.metric_keys`) and compares them against the tolerances. `scripts/consistency.py` is its deterministic first pass. Both exit 1 on a tolerance violation.

## Claims passport

One file per paper: `<outputs.dir>/passports/<document.slug>.yaml`. Numeric claims only; prose and citation claims belong to `/ploma:verify-claims`.

```yaml
paper:
  slug: <document.slug>
  title: <document.title>
  branch: <git branch>
  last_audit: <ISO-8601>
  last_audit_by: /ploma:audit-reproducibility
claims:
  - id: C1
    claim: "<number as stated in the manuscript>"
    location: "<file>:<table, figure or line>"
    source_file: <script that produced the value>
    source_line: <nearest line>
    output_file: <file under pipeline.outputs_dir>
    output_field: <key, one of pipeline.metric_keys>
    tolerance: {point_estimate: 0.01, n: exact}
    last_verified_on: <ISO-8601>
    last_verified_by: /ploma:audit-reproducibility
    status: PASS        # PASS | FAIL | STALE | UNVERIFIED
```

Status meaning: PASS within tolerance; FAIL outside tolerance; STALE when the source or output file changed after the last verification; UNVERIFIED when never audited.

Do not populate the passport without showing the inferred mapping to the author. Do not promote UNVERIFIED to PASS without running the audit. The passport never replaces `/ploma:verify-claims`.
