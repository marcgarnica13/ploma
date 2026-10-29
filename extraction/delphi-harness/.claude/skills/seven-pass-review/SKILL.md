---
name: seven-pass-review
description: Mechanize Pattern 15 — the seven-pass adversarial review protocol for grant proposals. Spawns 7 forked subagents in parallel (specific aims, significance, approach, preliminary evidence, budget/timeline, prose, citations/compliance), then synthesizes a prioritized revision checklist. Use for submission-ready or resubmission-stage proposals where single-pass review isn't enough.
argument-hint: "[proposal path]"
allowed-tools: ["Read", "Grep", "Glob", "Write", "Bash", "Task"]
effort: high
---

# Seven-Pass Adversarial Review

Runs seven independent reviewers, each focused on a single lens, then synthesizes their findings into one prioritized revision plan. Pattern 15 from the workflow guide, mechanized.

**Why seven passes?** A single-agent review blends lenses and softens each one. Seven forked agents each approach the proposal with full context budget for their own lens, then a synthesizer resolves conflicts and de-duplicates.

> **When to pick this over `/review-proposal`:** This skill costs roughly 7× more tokens than `/review-proposal` (default) and ~2× more than `/review-proposal --adversarial`. Use it when the proposal is submission-ready or at resubmission stage and you need maximum lens coverage. For early drafts or iterative work, `/review-proposal` is the right tool. For a panel-simulation pressure test, use `/review-proposal --panel <funder>` instead.

## Inputs

- `$0` — proposal path (`.tex`, `.md`, or `.pdf`). Defaults to `proposal/proposal_a4.tex`.

## The Seven Lenses

Each lens runs as a **forked subagent** (context: fork) so the main conversation stays clean.

| # | Lens | Focus | Agent type |
|---|---|---|---|
| 1 | Abstract / Specific Aims | Does the summary state the problem, aims, and expected payoff? Do the aims match the rest of the proposal? | general-purpose |
| 2 | Significance & Rationale | Is the problem important? Is the gap clearly stated? Is the scientific rationale sound? | general-purpose |
| 3 | Approach & Feasibility | Are the methods appropriate and justified? Are pitfalls and alternatives addressed? Can it be done with the requested resources/time? | domain-reviewer |
| 4 | Preliminary Evidence & Citations | Is the preliminary data sufficient to make the plan credible? Are claims to prior work accurate? | general-purpose |
| 5 | Budget & Timeline Realism | Is the budget complete and justified? Is the timeline realistic? Do milestones align with the aims? | general-purpose |
| 6 | Prose / Clarity | Sentence-level clarity, hedging, passive voice, paragraph cohesion | proofreader |
| 7 | Citations & Funder Compliance | Invokes `/validate-bib --semantic`; checks cite-claim direction for top-10 works; checks page/section-limit + required-section compliance | general-purpose |

## Workflow

### Phase 0: Pre-flight

1. Resolve proposal path.
2. Decide if `.pdf` → extract text first (`pdftotext -layout`).
3. Create output dir: `quality_reports/seven_pass_[stem]/`.

### Phase 1: Spawn 7 reviewers in parallel

In a single message, spawn 7 Task tool calls (one per lens). Each subagent gets:

- The proposal path (to re-read with its own context).
- The lens-specific prompt (below).
- Instructions to write to `quality_reports/seven_pass_[stem]/lens_[N]_[lens-name].md`.
- Severity tagging: CRITICAL / MAJOR / MINOR.

Lens prompt rubrics are embedded inline below — one summary paragraph per lens. Each forked subagent receives its lens's rubric plus the proposal path.

**Lens prompt summaries:**

- **Lens 1 (Abstract / Specific Aims):** Does the first sentence state the problem? Does it name the specific aims? State the expected payoff? Cross-check: do the aims stated here match the aims developed in the body, and are they independent enough that one aim's failure doesn't sink the project?
- **Lens 2 (Significance & Rationale):** Does the proposal open with the problem and why it matters? Is the gap in current knowledge/capability clearly stated? Is the scientific rationale sound and supported (hook → context → gap → significance)? Is the expected impact on the field articulated?
- **Lens 3 (Approach & Feasibility):** Are the methods appropriate to each aim and justified rather than arbitrary? Are pitfalls anticipated with alternative strategies? Is the research design sound? Can this team execute it with the requested resources in the proposed timeline? Are the aims sufficiently independent?
- **Lens 4 (Preliminary Evidence & Citations):** Is the preliminary data sufficient to make the plan credible (or, for exploratory mechanisms, is the absence justified)? Do figures/tables read standalone? Are claims attributed to prior work accurate in direction and source?
- **Lens 5 (Budget & Timeline Realism):** Is the budget complete and justified per line? Is the timeline (Gantt / milestone table) realistic for the scope? Do milestones map onto the aims? Is the requested duration matched to the work?
- **Lens 6 (Prose):** Sentences under 30 words? Active voice dominant? Hedging proportionate (neither overclaiming nor endless "may suggest")? Paragraph topic sentences?
- **Lens 7 (Citations & Compliance):** Invoke `/validate-bib --semantic`. For top-10 cited works, does the in-text claim match the cited work's actual finding direction? Are competing approaches cited fairly? Does the proposal comply with the funder's page/section limits and required-section list?

### Phase 2: Synthesize

Wait for all 7 lens reports. Then read them and produce:

`quality_reports/seven_pass_[stem]/_SYNTHESIS.md`

```markdown
# Seven-Pass Review: [Proposal]

**Date:** YYYY-MM-DD
**Path:** [proposal]

## Executive verdict

**Overall state:** [SUBMIT / REVISE-MINOR / REVISE-MAJOR / DECLINE-AND-RESTART]

## Cross-lens CRITICAL issues
| # | Lens(es) | Issue | Recommendation |
|---|---|---|---|

## MAJOR issues (second-round)
| # | Lens(es) | Issue |
|---|---|---|

## MINOR polish
[bulleted]

## Per-lens scorecard
| Lens | Critical | Major | Minor | Score/10 |
|---|---|---|---|---|
| 1. Abstract / Specific Aims | | | | |
| 2. Significance & Rationale | | | | |
| 3. Approach & Feasibility | | | | |
| 4. Preliminary Evidence & Citations | | | | |
| 5. Budget & Timeline Realism | | | | |
| 6. Prose | | | | |
| 7. Citations & Compliance | | | | |
| **Overall** | | | | |

## Revision plan (in recommended order)
1. [Highest-leverage fix — usually a lens with 2+ CRITICALs]
2. …
7. [Lowest-leverage polish]

## Contradictions between lenses
[If two lenses disagree, surface here. E.g., Lens 2 says "expand significance" but Lens 6 says "trim the rationale".]
```

### Phase 3: Token-budget report

After synthesis, print:

```
Seven-pass review complete.
Subagents: 7 (parallel) + 1 synthesizer.
Approx token usage: ~80–120k (vs ~15k for single-pass /review-proposal).
Runtime: ~3–5 min wall-clock.
For cheaper alternatives:
  - Single-pass: /review-proposal
  - Iterative: /review-proposal --adversarial
```

## When to use this skill

- **Before first submission** to a competitive funder.
- **After a major revision** when you want to catch drift.
- **Resubmission when panelists disagree** — surfaces contradictions your revision must navigate.

## When NOT to use

- Early drafts (use `/review-proposal` single-pass first).
- Short letters of intent, white papers, or pre-proposals (overkill).
- When you've already run this in the last 7 days and nothing substantive changed.

## Cross-references

- `.claude/skills/review-proposal/SKILL.md` — the single-pass and `--adversarial` modes (cheaper, faster).
- `.claude/skills/validate-bib/SKILL.md` — invoked by Lens 7.
- Workflow guide, Pattern 15 — the narrative explanation of why seven lenses.

## Exit behavior

- Exits 0 always (review is informational). The synthesis report's "Executive verdict" is the gate.
- Any `CRITICAL` at the top of the synthesis should block submission until resolved.

## What this skill does NOT do

- Re-run seven lenses if the proposal hasn't changed — check git diff against last run date in `_SYNTHESIS.md`, skip unchanged lenses if requested via `--incremental` (future).
- Auto-apply fixes — that's `/review-proposal --adversarial`'s job.
- Replace human judgment. A program officer who knows your funder still beats seven LLMs.
