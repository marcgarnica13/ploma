# Cross-artifact review (manuscript and pipeline)

Applies when `pipeline.enabled` is true in `ploma.yaml` and a manuscript review runs. A paper's numbers depend on the code that produced them; reviewing the text alone misses a whole class of errors.

## The dependency chain

```
manuscript claim -> table or figure -> results file under pipeline.outputs_dir
results file     -> script run from pipeline.run_from (pipeline.rerun)
script           -> library modules and data sources it reads
```

A bug anywhere upstream invalidates the claim downstream.

## Detection (conservative)

Run the protocol only when at least one signal is present:

- a figure carries a `% ploma:source <script> <args>` comment;
- numeric claims in the text sit next to a results directory at `pipeline.outputs_dir`;
- table or figure labels match file names or keys (`pipeline.metric_keys`) under `pipeline.outputs_dir`.

A manuscript with no pipeline signal skips the protocol, and `--no-cross-artifact` is then a no-op.

## Protocol

1. **Identify the producing scripts.** From the signals above, list the source files in `pipeline.language` that produced content in the manuscript.
2. **Review the code.** Dispatch the `ploma:code-reviewer` agent on each script. It reads `pipeline.gotchas` and `pipeline.env_contract`. Save reports under `<outputs.dir>/cross_artifact_<document.slug>/`.
3. **Audit the numbers.** Run `/ploma:audit-reproducibility` once on the manuscript and `pipeline.outputs_dir`. Save the report in the same directory.
4. **Report.** Add a section to the review:

```markdown
## Cross-artifact findings

**Scripts reviewed:** N
**Reproducibility:** PASS | FAIL, k of m claims within tolerance
**Code findings:** C critical, M major, L minor

### Critical (manuscript and code together)
| Manuscript claim | Code location | Issue |
|---|---|---|

### Code only (file a follow-up)
```

## Escalation

- A tolerance FAIL from the audit is CRITICAL in the manuscript review.
- A critical code bug that affects a manuscript claim is CRITICAL in the manuscript review.
- A critical code bug unrelated to any claim is a separate action item.

## Ordering

In `/ploma:review --peer` the cross-artifact pass runs first, so the editor's desk review can cite reproducibility evidence. In other modes it runs after the manuscript review.

## What this rule does not require

- Running the pipeline. The audit reads existing outputs.
- Git history archaeology. Review the current state.
- Judging code style for its own sake. What matters first is whether the results are defensible.
