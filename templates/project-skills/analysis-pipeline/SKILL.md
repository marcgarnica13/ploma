---
name: analysis-pipeline
description: Run, extend or debug this paper's analysis pipeline and produce results, tables and figures in its results directory (language, run directory and results directory are listed in the skill from ploma.yaml). Starts with a pre-flight report of the configured pipeline facts, follows the declared stage chain, respects the env contract and the known gotchas, and has the code reviewed before results are presented. Use when the user asks to analyse data, run or rerun the pipeline, add an analysis step, or regenerate results for the paper.
argument-hint: "[analysis goal, data source or stage]"
allowed-tools: Read, Grep, Glob, Write, Edit, Bash, Agent, Monitor
---

<!-- Created once by /ploma:onboard from ploma.yaml (pipeline block); this file is yours to edit.
     Adapted from the traces harness data-analysis skill: the project-specific stage chain,
     invariants and env variables are replaced by the values configured in ploma.yaml. -->

# Analysis pipeline

Run an end-to-end analysis on this paper's pipeline: read the inputs, run the stages, and produce publication-ready results, tables and figures.

Input: `$ARGUMENTS`, a data source, a stage, or a description of the analysis goal.

## Configured facts

These come from the `pipeline` block of `ploma.yaml` at the time this skill was created. When `ploma.yaml` changes, it wins; re-read it before relying on a value below.

- Language: {{ pipeline.language }}
- Run from: {{ _derived.run_from }}
- Rerun command: {{ _derived.rerun }}
- Results directory: {{ pipeline.outputs_dir }}
- Metric keys reported in the paper: {{ pipeline.metric_keys }}
- Stage chain: {{ _derived.stage_chain }}

Environment contract (variables the pipeline reads; never print their values or commit them):
{{ _derived.env_contract }}

Gotchas:
{{ _derived.gotchas }}

## Constraints

- Run every script from the run directory above, so relative paths and the env contract resolve.
- Check that each env contract variable is set (by name only) before running anything that reads it; a missing one stops the run and you ask the user.
- Save new scripts under the run directory with descriptive names; write outputs under the results directory, in a dated or named run subdirectory when the pipeline does not already do so.
- Preserve every invariant the gotchas name. When a change touches one, say so before making it.
- No hard-coded absolute paths or credentials; use the env contract.
- The `ploma:code-reviewer` agent reviews generated or changed code before results are presented.

## Phase 0: Pre-flight report

Before writing any analysis code, show that you read the inputs. This prevents invented field names and skipped conventions. Output this block in the reply:

```markdown
## Pre-flight report

**Pipeline (from ploma.yaml):** language, run directory, rerun command, results directory, metric keys, stage chain.
**Env contract:** each variable name, set or not set (never the value).
**Gotchas that apply to this task:** the relevant entries from the list above, or "none apply".
**Data source:** what was read, the fields or columns found, the row or record counts.
**Project conventions read:** the code style rules or docs found in the repo, one line each.
**Task interpretation:** one sentence restating what the user asked for.
**Plan:** three to five bullets, naming the stages that will run.
```

If an input cannot be read (an unset variable, an unreachable source, a missing file), stop and ask before going on.

## Phase 1: Setup and loading

1. A module header with title, purpose, inputs, outputs and the stage it belongs to.
2. Explicit imports or dependencies; respect any import-time env requirement the gotchas name.
3. A fixed seed, or a note on determinism, for every stochastic step.
4. Load the data through the project's own loading code where it exists, and inspect it before transforming it.

## Phase 2: Exploration

Print or save diagnostics before the main analysis: counts at each stage boundary (records in, records kept, records dropped by each filter), distributions of the key variables, and a few raw examples. An empty or near-empty output at any stage stops the run.

## Phase 3: Main analysis

Follow the stage chain. When it is "not declared", infer the stages from the code under the run directory, state them in the pre-flight report, and suggest adding them to `pipeline.stages` in `ploma.yaml`.

- Run exactly the configuration the user specifies; when none is given, use the one the paper reports.
- Evaluate on held-out data where the claim is generalisation, not only on the data used for fitting.
- Compare against at least one baseline, and run the ablations the claim needs.

## Phase 4: Publication-ready output

- Tables: the metric keys above, the configuration and N, exported in a machine-readable form (CSV or JSON) under the results directory and, when the paper includes them, as `.tex`.
- Figures: explicit dimensions, labelled axes and units, a legend, saved under the results directory.
- Every number that reaches the manuscript must be traceable to a file under the results directory.

## Phase 5: Save and review

1. Write all key metrics into the results directory.
2. Spawn the `ploma:code-reviewer` agent (Agent tool) on the generated or changed scripts: "Review <paths>; report only."
3. Address every Critical or High finding, especially those touching the gotchas, before presenting results.
4. If a reported number changed, run /ploma:audit-reproducibility to compare the manuscript against the new results.

## Long runs

For a run that takes more than a couple of minutes, launch it with Bash and `run_in_background: true`, then use the Monitor tool on it until a milestone line appears (for example a metrics file written) or the process exits. Do not poll with sleep loops.

## Important

- Reproduce, do not guess: when a configuration is given, run exactly that.
- Show the work: print counts and distributions before the main analysis.
- Check for silent failures: empty filter output, dtype drift on join keys, results written to an unexpected directory, a source that returned nothing without an error.
