# Claims passport

One file per paper at `<outputs.dir>/passports/<document.slug>.yaml`. It records, for each numeric claim of a result, where the number comes from and how its last check went. Schema: `${CLAUDE_PLUGIN_ROOT}/schemas/passport.schema.json`. Scope: numbers only (metric values, counts, percentages in text, tables and captions). Prose and citation claims belong to `/ploma:verify-claims`.

`/ploma:audit-reproducibility` creates it when absent and updates it in place; `scripts/consistency.py` reads it (a FAIL or STALE claim is a consistency FAIL, an UNVERIFIED claim an INFO line). A FAIL claim whose number no longer appears anywhere in the file its `location` names (the whole file, since cited lines shift) is reported as `consistency.passport_stale.<id>` WARN instead: the manuscript was corrected after the audit, so re-run `/ploma:audit-reproducibility`. The passport is never required by the commit gate.

## Example

```yaml
paper:
  slug: main
  title: "A Method for Ranking Things"
  branch: main
  last_audit: "2026-10-29T10:00:00Z"
  last_audit_by: /ploma:audit-reproducibility
claims:
  - id: C1
    claim: "average fitness of 0.81"
    location: "sections/results.tex:Table 1, row Ours, column Avg. fitness"
    source_file: scripts/evaluate.py
    source_line: 42
    output_file: results/metrics.json
    output_field: avg_fitness
    tolerance: {point_estimate: 0.01}
    last_verified_on: "2026-10-29T10:00:00Z"
    last_verified_by: /ploma:audit-reproducibility
    status: PASS
    notes: "computed 0.8098; diff 0.0002"
  - id: C2
    claim: "12 teams"
    location: "main.tex:15"
    source_file: null
    source_line: null
    output_file: results/metrics.json
    output_field: n_teams
    tolerance: {n: exact}
    last_verified_on: null
    last_verified_by: null
    status: UNVERIFIED
    notes: "matched by name only; confirm the source script"
```

## Fields

- `paper`: `slug` is `document.slug`; `title` is `document.title`; `branch` comes from `git rev-parse --abbrev-ref HEAD` (null outside git); `last_audit` and `last_audit_by` are set on every run.
- `id`: stable, `C<n>`. A new claim takes the next free number. Ids are never reused or renumbered.
- `claim`: the number as the manuscript states it, with a few words of context.
- `location`: `<file>:<line>`, or the table, row and column for a cell.
- `source_file`, `source_line`: the script that produced the value and the nearest line, when known; null otherwise. Source-line inference is best effort; the author confirms it.
- `output_file`, `output_field`: the file under `pipeline.outputs_dir` and the key or column holding the value.
- `tolerance`: optional per-claim override of `pipeline.tolerances`, such as `{point_estimate: <value>}` or `{n: exact}`.
- `last_verified_on`, `last_verified_by`: set when the claim is checked in this run.
- `status`: PASS, FAIL, STALE or UNVERIFIED.
- `notes`: the computed value and the difference, or why the claim could not be checked.

## Status rules

- **PASS**: the last check found the claim within tolerance.
- **FAIL**: outside tolerance. The note gives the computed value and the difference.
- **STALE**: `source_file` or `output_file` changed after `last_verified_on`, or the claim no longer appears in the manuscript. A STALE claim whose files changed is checked again in the same run and becomes PASS or FAIL; it stays STALE only when it cannot be re-checked (the claim is gone, or its output file is missing).
- **UNVERIFIED**: never checked, or the match had low confidence. Never promote it to PASS without the numeric check.

## Writing rules

- The skill never deletes an entry. A retracted claim stays STALE until the author removes it or updates its `location`.
- Show the author the inferred mapping before writing new entries.
- Keep every string on one line, in double quotes when it holds a colon or a `#`. No block scalars (`|` or `>`), anchors or multi-line strings: the fallback YAML loader does not read them.
- Flow maps (`{n: exact}`) and lists are fine. Timestamps are ISO 8601 in UTC, quoted.
- After writing, validate with `scripts/consistency.py --passport <path>`; a `consistency.passport_invalid` finding names the schema problem.
