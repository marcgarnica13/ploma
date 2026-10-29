---
description: Paper ↔ code cross-artifact review — when /review-paper runs, auto-invoke the python-reviewer agent on referenced scripts and /audit-reproducibility on the pair. Surface cross-artifact findings alongside the paper review.
globs: ["manuscript/**/*.tex", "*.tex", "src/**/*.py"]
alwaysApply: false
---

# Cross-Artifact Review Protocol

A paper is not an island. Its claims depend on the code that produced them. Reviewing the paper without reviewing the pipeline is reviewing half the artifact.

## The Dependency Graph

```
samplepaper.tex ──cites──> Table 1 / Fig 3 (avg fitness)
Table 1         ──from──> src/results/offensive_statsbomb_pass_09x/metrics.json
metrics.json    ──by──> src/notebooks/discovery/parse_statsbomb_matches.py
parse_*.py      ──uses──> sports_pm.logic.discovery (create_event_log, get_heuristic_net)
discovery       ──uses──> sports_pm.logic.filters (filter_offensive_sequences)
filters         ──reads──> MongoDB (statsbomb_lake / staging_soccerlogs)
```

A bug in `filters.py` invalidates Table 1. Reviewing `samplepaper.tex` without touching the pipeline misses this class of error entirely.

## When to apply

Applies when `/review-paper` runs on a manuscript that references the pipeline. Detection is **pattern-based** — if the manuscript has none of the signals below, no cross-artifact work happens (and `--no-cross-artifact` is a no-op). To force invocation, invoke the `python-reviewer` agent and `/audit-reproducibility` directly alongside `/review-paper`.

Detection signals:

- Figures `fig1-5.pdf` traceable to a `src/` run, or `%% source: src/...` comments
- Numeric claims in text (fitness/metric values, possession/case counts, percentages) **combined with** a sibling `src/` pipeline and `src/results/` output dirs
- Table/figure labels in the paper that match filenames or fields under `src/results/`

Detection is intentionally conservative — a paper with no associated pipeline output should not trigger the protocol.

## The protocol

When `/review-paper` detects any of the above:

### 1. Identify referenced scripts

Scan the manuscript for:

- Figures/tables traceable to a pipeline run (`fig1-5.pdf`, `%% source: src/...` comments)
- Numeric claims matching fields/filenames under `src/results/`

Build a list of `src/**/*.py` modules/scripts that produced content in this paper (typically the
discovery scripts in `src/notebooks/discovery/` plus the `sports_pm` modules they call).

### 2. Auto-invoke the `python-reviewer` agent

For each identified Python script/module, launch the `python-reviewer` agent in a forked subagent (`context: fork`). Save reports to `quality_reports/cross_artifact_[paper]/python_review_[script].md`.

### 3. Auto-invoke `/audit-reproducibility`

Run `/audit-reproducibility manuscript/samplepaper.tex src/results/` once. Save to `quality_reports/cross_artifact_[paper]/reproducibility.md`.

### 4. Surface cross-artifact findings

In the paper review report, add a new section:

```markdown
## Cross-Artifact Findings

**Scripts reviewed:** N (see `quality_reports/cross_artifact_[paper]/`)
**Reproducibility:** PASS / FAIL — k of m claims within tolerance
**Code quality (merged from python-reviewer reports):** C critical, M major, L minor

### Critical cross-artifact issues (paper + code together)
| Paper claim | Code location | Issue |
|---|---|---|

### Code-only issues (won't block paper, but file a follow-up)
…

### Paper-only issues (code is clean)
[Rest of the paper review goes here]
```

### 5. Exit behavior

- Any CRITICAL from `/audit-reproducibility` (FAIL on tolerance) → escalate to CRITICAL in paper review.
- Code CRITICAL bugs that affect paper claims → escalate in paper review.
- Code CRITICAL bugs unrelated to paper claims → file as separate action item.

## Opt-out

- `/review-paper --no-cross-artifact` skips the dependency graph. Useful for theory papers, comments, or preprints without code.

## Cross-references

- `.claude/skills/review-paper/SKILL.md` — the orchestrator.
- `.claude/agents/python-reviewer.md` — code reviewer.
- `.claude/skills/audit-reproducibility/SKILL.md` — numeric claims verifier.
- `.claude/rules/replication-protocol.md` — tolerance contract.

## What this rule does NOT require

- Running the Python pipeline / MongoDB (that's `/audit-reproducibility`'s job, and it reads existing outputs).
- Git-blame archaeology — we review current state.
- Judging whether a paper's authors wrote good code vs. whether their *results* are defensible. We care about the latter first.

## `--peer` mode ordering

In `/review-paper --peer [journal]` mode, cross-artifact review runs **before** the editor's desk review (as Phase 0). This gives the editor reproducibility evidence — any FAIL on load-bearing claims is desk-reject-worthy. The editor's desk review will cite specific `/audit-reproducibility` findings in the desk_review.md when relevant.

In default and `--adversarial` modes, cross-artifact still runs at Step 6b (after the paper review). Both orderings are valid; the `--peer` pre-flight ordering exists because editors make desk-reject decisions based on evidence of data errors.

