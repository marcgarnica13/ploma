---
name: audit-reproducibility
description: Enforce the replication-protocol.md rule by cross-checking numeric claims in the manuscript against the actual Python pipeline outputs. Report PASS/FAIL per claim against tolerance thresholds. Use before submission and before releasing the code/data package.
argument-hint: "[manuscript path] [outputs-dir] (outputs-dir defaults to src/results/)"
allowed-tools: ["Read", "Grep", "Glob", "Write", "Bash", "Task", "Monitor"]
effort: high
---

# Audit Reproducibility

Compare numeric claims in a manuscript (point estimates, standard errors, p-values, counts) against the actual outputs produced by the analysis pipeline. Report PASS / FAIL per claim against the tolerance thresholds defined in [`.claude/rules/replication-protocol.md`](../../rules/replication-protocol.md).

**Core principle:** If the paper says `avg fitness = 0.81` and the pipeline produces `0.806`, we verify — **numerically** — that the difference is within the documented tolerance. No more "looks close enough" eyeballing.

## When to use

- **Before submission.** Catches the "I updated the analysis but forgot to update Table 2" bug.
- **Before releasing a replication package.** Verifies the code actually reproduces the paper.
- **After a major revision.** Ensures the paper still matches the latest code.
- **Quality-gate in `/commit`.** Pair with a pre-commit invocation on manuscript + analysis changes.

## Inputs

- `$0` — path to the manuscript (`.tex`, `.md`, `.pdf`). Defaults to `manuscript/samplepaper.tex`.
- `$1` — path to the outputs directory. Defaults to `src/results/` (timestamped result dirs such as `src/results/offensive_statsbomb_pass_09x/`). Any directory the user-specified outputs live in is accepted.

## Workflow

### Phase 0: Pre-flight

1. Read [`replication-protocol.md`](../../rules/replication-protocol.md) for the tolerance thresholds currently in effect.
2. Verify the outputs directory exists and is non-empty. If empty or stale (older than the manuscript), prompt the user to re-run the pipeline (run from `src/`, e.g. `python notebooks/discovery/parse_statsbomb_matches.py` with the env-var contract set) before auditing. Note the **MongoDB caveat**: exact reproduction depends on the same data snapshot being available.
3. Ensure an environment capture exists (e.g., the pinned `src/requirements.txt` and a note of the Mongo data snapshot / result dir used).

### Phase 1: Extract claims from the manuscript

Parse the manuscript for numeric claims. Patterns to match:

- **Metric values**: `average fitness = 0.81`, `$\text{fitness} = 0.806$`, `generalization = 0.74`
- **Table cells**: `& 0.81 & 0.74 &` in LaTeX table environments
- **Counts**: `12,430 offensive possessions`, `$N = 12{,}430$`, `across 64 matches`
- **Summary stats**: `mean fitness = 0.78`, `SD = 0.05`
- **Percentages / shares**: `38% of possessions reach the box`

Record each claim as a tuple:

```
{
  claim_id: "Table1_avg_fitness",
  location: "Table 1, row 'Offensive net', col 'avg fitness'",
  kind: "metric" | "count" | "percentage",
  reported_value: 0.81,
  raw_context: "the offensive net attains an average fitness of 0.81..."
}
```

Write the extracted claims to `quality_reports/reproducibility_claims_[manuscript-name].json` so the user can review the extraction before audit.

### Phase 2: Extract results from outputs

Scan `$1` for corresponding values. Priority order:

1. **`.json` metrics files** — direct key lookup (e.g., `metrics.json["avg_fitness"]`). The discovery pipeline's natural output format.
2. **`.csv` summary files** — `pandas.read_csv`, key-value / column lookup.
3. **`.tex` tables** — parse LaTeX table cells directly; match on column headers + row labels.
4. **`.pkl` / `.parquet`** — `pickle.load` / `pandas.read_parquet` for serialized intermediate results.
5. **Run logs** — regex extraction of printed metric lines.

Record each extracted result:

```
{
  source: "src/results/offensive_statsbomb_pass_09x/metrics.json",
  lookup_key: "avg_fitness",
  value: 0.806,
  dependency: 0.9
}
```

### Phase 3: Match claims to results

Use fuzzy heuristics when exact labels don't match:

- Name similarity (`"average fitness"` ~ `"avg_fitness"` ~ `"mean fitness"`)
- Magnitude similarity (if two candidates have values within 10% of the reported, prefer the one whose config (e.g., dependency threshold, data source) matches the paper)
- Context hints from the claim's `raw_context` field (table number, row label, description)

For every claim, produce a match candidate with a confidence score. Claims below 0.7 confidence get flagged as "UNMATCHED — manual review needed" rather than silently passing.

### Phase 4: Tolerance check

For each matched claim, apply the thresholds from `replication-protocol.md`:

| Kind | Tolerance | Example |
|---|---|---|
| Integers (N possessions, match/case counts) | Exact | 12,430 must equal 12,430 (for the same Mongo snapshot) |
| Metric point values (fitness) | `abs(reported - computed)` < 0.01 | 0.81 vs 0.806 → diff = 0.004 → PASS |
| Aggregate/generalization scores | `abs(reported - computed)` < 0.02 | 0.74 vs 0.755 → diff = 0.015 → PASS |
| Percentages / shares | ±0.1pp | 38.0% vs 38.05% → PASS |

Respect any **tolerance overrides** the user has written into their `replication-protocol.md` fork. Note the **MongoDB caveat**: integer counts can diverge if the data snapshot differs — flag such cases rather than silently failing.

### Phase 5: Report

Write `quality_reports/reproducibility_audit_[manuscript-name].md`:

```markdown
# Reproducibility Audit: [Manuscript Title]

**Date:** [YYYY-MM-DD]
**Manuscript:** [path]
**Outputs directory:** [path]
**Tolerance source:** .claude/rules/replication-protocol.md

## Summary

| Status | Count |
|---|---|
| PASS | N |
| FAIL (diff > tolerance) | M |
| UNMATCHED (manual review) | K |
| **Overall verdict** | **PASS / FAIL** |

## PASS (all within tolerance)
| Claim | Reported | Computed | Diff | Tolerance |
|---|---|---|---|---|
| Table1_avg_fitness | 0.81 | 0.806 | 0.004 | 0.01 |

## FAIL (outside tolerance — BLOCKER)
| Claim | Reported | Computed | Diff | Tolerance | Location in paper |
|---|---|---|---|---|---|

## UNMATCHED (manual review)
| Claim | Raw context | Candidate sources |
|---|---|---|

## Environment
[pinned src/requirements.txt versions; Mongo database + data snapshot; result dir used]

## Next steps
1. Fix any FAIL rows — either update the manuscript or rerun the pipeline.
2. Review UNMATCHED rows — add explicit lookup keys or widen the search scope.
3. After zero FAILs, the paper is replication-ready.
```

## Exit behavior

- **All PASS:** exit 0, summary printed.
- **Any FAIL:** exit 1, summary printed to stderr. This makes the skill usable as a `/commit` pre-commit gate — see `replication-protocol.md` for the enforcement pattern.
- **UNMATCHED > 0 (with 0 FAIL):** exit 0 with warning — user must manually review.

## Output coverage

The skill compares manuscript claims against the Python pipeline's outputs:

| Output kind | Default location | Read-output via | Common claim sources |
|---|---|---|---|
| Metrics JSON | `src/results/<run>/` | `json.load` | `avg_fitness`, `generalization`, `dependency` |
| CSV summaries | `src/results/<run>/` | `pandas.read_csv` | per-match / per-config metric tables |
| Serialized intermediates | `src/results/<run>/` | `pandas.read_parquet`, `pickle.load` | possession counts, event-log stats |
| LaTeX tables | `manuscript/` | parse cells directly | values `\input`/typed into the paper |

**Process-mining notes:**

- The strongest provenance signal is a metrics file in a timestamped result dir whose name encodes the
  config (e.g., `offensive_statsbomb_pass_09x` → StatsBomb source, dependency 0.9). Match the paper's
  reported config to the dir name.
- Integer counts (possessions, cases) depend on the **MongoDB data snapshot**. A mismatch at the
  count level usually means a different snapshot, not a code bug — flag it as a data-availability
  caveat rather than a hard FAIL.

## Passport-mode (v1.9.0)

When `quality_reports/passports/<paper-slug>.yaml` exists, the skill operates in **passport mode**: instead of emitting a one-shot report, it **reads, updates, and rewrites** the passport file in place.

- For each `claims:` entry in the passport, perform the same numeric audit as the default mode (extract reported value from manuscript at `location`, locate computed value at `source_file:source_line` / `output_file:output_field`, compare against `tolerance:`).
- After each claim is audited, update `status` in place:
  - PASS → claim within tolerance.
  - FAIL → claim outside tolerance. Record the discrepancy in the entry's `notes`.
  - STALE → if `source_file` or `output_file` modification time is later than `last_verified_on`, mark STALE and re-run the audit logic (after the rerun, status becomes PASS or FAIL — STALE is transient).
- Update `last_verified_on` and `last_verified_by: "/audit-reproducibility"` per claim.
- Update `paper.last_audit` at the top level.

If a claim in the manuscript is detected that has no matching passport entry, emit an UNVERIFIED warning — the author should add it (passport scope is author-curated, not auto-populated, to avoid bad inferences).

Passport mode does NOT delete passport entries. If a claim disappears from the manuscript, the passport entry remains with a STALE status — the author decides whether to delete (claim retracted) or update the entry's `location` (claim moved).

See [`.claude/rules/replication-protocol.md`](../../rules/replication-protocol.md) "Claims Provenance: `passport.yaml`" for the full schema and integration points (`/commit`, `/review-paper`).

## Cross-references

- [`.claude/rules/replication-protocol.md`](../../rules/replication-protocol.md) — the tolerance contract + passport schema.
- [`.claude/agents/python-reviewer.md`](../../agents/python-reviewer.md) — catches code-quality issues; this skill catches NUMERICAL reproducibility.
- [`.claude/skills/review-paper/SKILL.md`](../review-paper/SKILL.md) — content review; pair with this skill for a full pre-submission audit.

## What this skill does NOT do

- **Re-run your analysis.** The skill compares CURRENT outputs against manuscript claims. If the outputs are stale, re-run the pipeline first (the pre-flight phase will warn).
- **Catch wrong method choices.** A pipeline that runs cleanly and produces a reproducible `0.81` is reproducible. Whether `0.81` is measured on the RIGHT (held-out) data, or whether fitness is the right metric, is a `review-paper` / domain-reviewer question.
- **Check external package versions.** Pinning versions is on the user (via `src/requirements.txt`); the env capture lets a reviewer see what was used.

## Long batch reruns: use the Monitor tool (Apr 2026)

When `/audit-reproducibility` is asked to verify *all* numeric claims in a paper, the safest approach is to re-run the pipeline (from `src/`, e.g. `python notebooks/discovery/parse_statsbomb_matches.py`) and compare the regenerated outputs to the manuscript values. For runs that take more than a couple of minutes, background-launch the rerun and use Anthropic's **Monitor tool** (Apr 2026 Week 15) to stream stdout. The audit can react to errors mid-stream rather than waiting for the entire pipeline to finish before noticing a failed step.
