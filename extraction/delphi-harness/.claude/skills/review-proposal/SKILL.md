---
name: review-proposal
description: Comprehensive grant-proposal review with three modes: single-pass (default), --adversarial critic-fixer loop, and --panel [funder] simulated panel-review pipeline (program officer + 2 dispositioned panelists + funding decision, calibrated to a target funder such as NIH/NSF/ERC). Resubmission continuation via --panel --r2/--r3; hostile-panel stress test via --panel --stress; panelist-disposition variance reporting via --panel --variance N.
argument-hint: "[proposal path] [--adversarial | --panel <funder> [--r2 | --r3 | --stress | --variance N] [--no-novelty-check]]"
allowed-tools: ["Read", "Grep", "Glob", "Write", "Edit", "Bash", "Task"]
---

# Grant Proposal Review

Produce a thorough, constructive review of a grant proposal — the kind of critique a funder's review panel would write.

> **Which review skill do I want?**
>
> - **`/review-proposal`** (this skill) — single comprehensive report, optional `--adversarial` critic-fixer loop, or `--panel <funder>` simulated panel-review pipeline. Best for **most drafts**.
> - **`/seven-pass-review`** — seven independent lenses in parallel (specific aims, significance, approach, preliminary evidence, budget/timeline, prose, citations/compliance) then synthesized. Heavier (7× token cost). Best for **submission-ready proposals** or **resubmission stage** where you need maximum coverage.
> - **`/respond-to-reviewers`** — if you already have a panel critique and need a response document, not another review.

**Input:** `$ARGUMENTS` — path to a proposal (`.tex` or `.pdf`); defaults to `proposal/proposal_a4.tex`. Optional flags:

- `--adversarial` — critic-fixer loop (max 5 rounds).
- `--panel <FUNDER>` — simulated panel review pipeline calibrated to `<FUNDER>` (see `.claude/references/funder-profiles.md` for available short names).
- `--r2` / `--r3` — resubmission continuation mode (requires `--panel`). Reloads prior round, classifies concerns Resolved / Partial / Not addressed.
- `--stress` — hostile-panel stress test (requires `--panel`). Forces SKEPTIC dispositions, doubles critical peeves.
- `--variance` (followed by integer **N**, default 3) — panelist-disposition variance mode (requires `--panel`). Runs **N** panelists with **independently sampled** dispositions from the 6-way taxonomy. Program officer aggregates into a **decision distribution**, not a point estimate. Mutually exclusive with `--stress` and `--r2`/`--r3`.
- `--no-novelty-check` — skip program officer's WebSearch prior-art probe (default is ON).

> **Already received a panel critique?** Use [`/respond-to-reviewers`](../respond-to-reviewers/SKILL.md) instead. That skill cross-references each panel concern against the revised proposal and drafts a complete response document.

---

## Modes

### Default mode (single-pass)

One comprehensive review report. Fast, low token cost, suitable for early drafts where the PI wants feedback and will iterate manually.

### Adversarial mode (`--adversarial`)

Iterative critic-fixer loop. The critic identifies issues, the fixer proposes and applies edits (with user approval), and the critic re-audits. Loops until APPROVED or max 5 rounds.

Use when: preparing a pre-submission draft, responding to a prior decline with substantive revisions, or after your own major rewrite. Costs more tokens but produces a proposal the critic has signed off on.

### Panel-review mode (`--panel <FUNDER>`)

Simulated panel pipeline: **program-officer desk review → panelist selection → 2 panelists with different dispositions → funding-decision synthesis**. Calibrated to a target funder from `.claude/references/funder-profiles.md`. Use when: pre-submission dress rehearsal, choosing between target programs, resubmission planning.

This mode is materially different from `--adversarial`: adversarial runs the same critic 5× with fresh context; `--panel` runs **different personas** (program officer + 2 dispositioned panelists drawn from the 6-way taxonomy: SIGNIFICANCE / INNOVATION / APPROACH-FEASIBILITY / TEAM-INVESTIGATORS / BROADER-IMPACT / SKEPTIC) whose priors are *deliberately different* and who are blind to each other.

**Agents used** (all reimplemented in this template; adapted from [Hugo Sant'Anna's clo-author](https://github.com/hugosantanna/clo-author) with permission):

- `.claude/agents/editor.md` — program officer (desk review, panelist selection, synthesis).
- `.claude/agents/domain-referee.md` — substance panelist.
- `.claude/agents/methods-referee.md` — methodology panelist (proposal-type-aware).

**Sub-flags:**

- `--r2` / `--r3` — resubmission mode. Skips fresh desk review; reloads prior round's reports; same panelists + dispositions + peeves; classifies each prior concern as Resolved / Partial / Not addressed. Hard cap at `--r3` (no round 4+).
- `--stress` — Hostile panel. Forces both panelists to SKEPTIC disposition, doubles critical peeves, framing: "you are looking for reasons to decline this proposal." Output is a concern-list gauntlet, not a decision letter.
- `--variance` (with integer **N**, default 3) — Panelist-disposition variance mode. Runs **N** panelists with **independently sampled** dispositions from the 6-way taxonomy (SIGNIFICANCE / INNOVATION / APPROACH-FEASIBILITY / TEAM-INVESTIGATORS / BROADER-IMPACT / SKEPTIC). Program officer synthesizes into a **distribution of decisions**, not a single verdict. See "Variance mode" below.
- `--no-novelty-check` — Disables the program officer's WebSearch prior-art probes (default is ON). Use in offline or hallucination-sensitive contexts. **Prior-art-check caveat (document this to users):** WebSearch can return hallucinated citations or miss paywalled recent work. Always surface prior-art-probe results as flags for manual verification, not verdicts.

#### Variance mode (`--panel --variance N`)

**Why this mode exists.** Default `--panel` runs a program officer + 2 panelists with dispositions sampled once. A single panel-review pass is a point estimate of how the proposal would fare — but the AgentReview ACL 2024 study ([arXiv:2406.12708](https://arxiv.org/abs/2406.12708)) found that **~37% of decisions vary purely from reviewer-disposition sampling** and another 27.7% from partial identity disclosure. A point estimate hides this variance.

Variance mode runs N independent panelists (default N=3, max N=5 for token-cost discipline) with disposition sampling, then reports a **decision distribution** that surfaces this variance to the PI.

**How it works:**

1. Program officer performs desk review once (shared across the N panelists).
2. The program officer samples N dispositions from the 6-way taxonomy **with replacement**. Stratification rule: if N ≥ 3, at least one SKEPTIC is always sampled (avoids drawing N friendly panelists by chance).
3. Each of the N panelists runs in an isolated context (`Task` with `context: fork`) — same proposal, same proposal-type rubric, different disposition. Panelists are blind to each other.
4. Program officer receives N independent reports and produces:
   - A **decision-distribution table** (e.g., `2/3 REVISE, 1/3 DECLINE` with the modal verdict highlighted).
   - A **concern-frequency table** showing which concerns appeared across multiple panelists (high frequency = robust criticism; low frequency = disposition-dependent).
   - A **program-officer recommendation** that explicitly references the variance ("modal verdict REVISE, with one SKEPTIC dissent on feasibility — PI should address the feasibility concern even though it's not the majority position").

**Output files:**

- `quality_reports/panel_review_<proposal>/panelist_1.md` … `panelist_N.md` (per-panelist reports)
- `quality_reports/panel_review_<proposal>/decision_distribution.md` (aggregate table + concern-frequency analysis)
- `quality_reports/panel_review_<proposal>/program_officer_synthesis.md` (final decision letter)

**Cost discipline.** Variance mode multiplies panelist-tier cost by N relative to default `--panel` (which runs 2 panelists). The Cost-Conscious Composition section of the workflow guide recommends keeping panelists on Sonnet (mid-tier) for variance runs and reserving Opus for the program-officer synthesis. Hard cap at N=5; for higher variance estimates, run `--variance 5` twice and combine offline.

**Mutual exclusivity.** Variance mode cannot combine with `--stress` (which forces SKEPTIC×2 and would defeat the sampling purpose) or `--r2`/`--r3` (which reuses prior-round dispositions for continuity). The skill halts with an error if mutually-exclusive flags are combined.

**When to reach for it:**

- Pre-submission dress rehearsal where you want to know not just "will this proposal get funded" but "*how confidently* will it get funded."
- Deciding between target programs — run `--variance 3` against two funder profiles, compare distributions.
- Responding to a decline where the panel felt unrepresentative — `--variance 5` against the same funder profile gives an empirical sense of whether the original panelists were typical.

---


## Steps (both modes)

1. **Locate and read the proposal.** First strip flags (`--adversarial`, etc.) from `$ARGUMENTS` to get the bare proposal path. Check:
   - Direct path (bare path from step 1)
   - Default to `proposal/proposal_a4.tex` if no path is given
   - Glob `proposal/*.tex` / `*.pdf` for partial matches

2. **Read the full proposal** end-to-end with the Read tool — a 1M-token window holds a full proposal. For long PDFs, page through with the `pages` parameter (up to 20 pages per request).

3. **Evaluate across 6 dimensions** (see below).

4. **Generate 3–5 "panelist objections"** — the tough questions a tough panelist would ask.

5. **Produce the review report.**

6. **Save to** `quality_reports/proposal_review_[sanitized_name]_round[N].md` (N=1 in default mode; N increments in adversarial mode).

7. **If `--adversarial` is in `$ARGUMENTS`:** invoke the critic-fixer loop defined in the next section. Otherwise stop here.

---

## Review Dimensions

The six funder-agnostic grant dimensions (blended from NIH / NSF / ERC).

### 1. Significance
- Is the problem important — would solving it move the field or address a real need?
- Is the gap in current knowledge or capability clearly stated?
- Are the specific aims well-defined and consequential?
- Is the expected payoff articulated (what changes if this succeeds)?

### 2. Innovation
- Is the idea genuinely novel, or an incremental extension?
- Does it challenge or shift a current paradigm, concept, or method?
- Is the novelty over prior art (including the team's own prior work) clearly differentiated?

### 3. Approach & Feasibility
- Is the research design sound and clearly described?
- Are the methods appropriate to the aims, and justified rather than arbitrary?
- Are the aims sufficiently independent that one aim's failure does not sink the project?
- Are pitfalls anticipated with alternative strategies?
- Can this be executed with the requested resources in the proposed timeline?

### 4. Investigators / Team
- Does the team have the track record and expertise for this work?
- Is preliminary evidence sufficient to make the plan credible?
- Are roles and the collaboration structure clear?
- Is the institutional environment adequate (facilities, resources, support)?

### 5. Broader Impact
- Is there a concrete plan for impact beyond the immediate results (dissemination, training, broadening participation, application)?
- Is it specific and assessable, not boilerplate?
- Does it align with the funder's mission?

### 6. Funder Fit & Compliance
- Does the proposal fit this funder's stated priorities and program scope?
- Does it comply with format rules (page/section limits, required sections, eligibility)?
- Are budget and timeline complete, realistic, and justified?
- Is the proposal the right length and structure for the call?

---

## Output Format

```markdown
# Proposal Review: [Proposal Title]

**Date:** [YYYY-MM-DD]
**Reviewer:** review-proposal skill
**File:** [path to proposal]

## Summary Assessment

**Overall recommendation:** [FUND / REVISE / DECLINE]

[2-3 paragraph summary: the core idea, strengths, and key concerns]

## Strengths

1. [Strength 1]
2. [Strength 2]
3. [Strength 3]

## Major Concerns

### MC1: [Title]
- **Dimension:** [Significance / Innovation / Approach & Feasibility / Investigators / Broader Impact / Funder Fit & Compliance]
- **Issue:** [Specific description]
- **Suggestion:** [How to address it]
- **Location:** [Section/page/aim if applicable]

[Repeat for each major concern]

## Minor Concerns

### mc1: [Title]
- **Issue:** [Description]
- **Suggestion:** [Fix]

[Repeat]

## Panelist Objections

These are the tough questions a tough panelist would likely raise:

### PO1: [Question]
**Why it matters:** [Why this could sink the proposal]
**How to address it:** [Suggested response or additional evidence]

[Repeat for 3-5 objections]

## Specific Comments

[Section-by-section comments, if any]

## Summary Statistics

| Dimension | Rating (1-5) |
|-----------|-------------|
| Significance | [N] |
| Innovation | [N] |
| Approach & Feasibility | [N] |
| Investigators / Team | [N] |
| Broader Impact | [N] |
| Funder Fit & Compliance | [N] |
| **Overall** | **[N]** |
```

---

## Principles

- **Be constructive.** Every criticism should come with a suggestion.
- **Be specific.** Reference exact sections, aims, budget lines, milestones.
- **Think like a panelist at the target funder.** What would make them decline?
- **Distinguish fatal flaws from minor issues.** Not everything is equally important.
- **Acknowledge what's done well.** Strong proposals deserve recognition.
- **Do NOT fabricate details.** If you can't read a section clearly, say so.

---

## Adversarial Mode — Critic-Fixer Loop

**Only runs if `--adversarial` is in `$ARGUMENTS`.**

This critic-fixer loop replaces the manual fix-and-resubmit cycle the single-pass review otherwise leaves PIs doing.

### Flow

```
Phase 0: Pre-flight
  │
  ├─ Verify the proposal compiles (`cd proposal && make all`) if applicable
  ├─ Snapshot the pre-review version: git stash OR copy to a .review-backup/
  │
Phase 1: Critic audit (round N=1,2,3,...)
  │
  ├─ Run the default review above, producing a round-N report
  ├─ If the report has ZERO Major Concerns and ZERO Panelist Objections
  │  rated "fatal":
  │     → VERDICT = APPROVED. Stop the loop. Write final summary.
  │  Else: continue.
  │
Phase 2: Fixer
  │
  ├─ For each Major Concern in the round-N report, produce a concrete
  │  proposed edit (diff or new text block).
  ├─ Present proposed edits to the user grouped by severity (Critical →
  │  Major → Minor). Ask for approval: "apply all", "apply critical+major
  │  only", "review each", or "abort".
  ├─ Apply approved edits with the Edit tool.
  ├─ If the proposal is a compile target (`.tex`), re-compile via
  │  `cd proposal && make all` and verify it still builds.
  │
Phase 3: Re-audit
  │
  └─ Spawn a FRESH-CONTEXT subagent (via Task, `subagent_type` set to
     general-purpose) to re-read the proposal and produce a round-(N+1)
     report. Fresh context prevents anchoring bias — the new reviewer
     sees the edited proposal, not the diff.
     → Jump back to Phase 1.
```

### Iteration limits

- **Max 5 rounds.** After round 5, halt regardless of verdict.
- **Fix round limits:** if the same Concern label appears in rounds N and N+2, flag as "author disagreement" and let the user decide (keep-as-is with rationale vs. another fix attempt).
- **Budget escape:** if cumulative token cost across all rounds exceeds a configurable spend cap (default ~500k — a spend ceiling, not a context-window limit, since each re-audit runs in fresh context), warn and let the user cap further rounds.

### Stopping criteria

| Condition | Action |
|---|---|
| Zero Major Concerns, zero fatal Panelist Objections | APPROVED — final summary |
| Max 5 rounds reached | HALTED — list remaining concerns, user decides |
| User approves zero fixes in a round | HALTED — user signals "I disagree with this review" |
| Compile fails after applied fixes | ROLLED BACK to pre-round-N snapshot, report compile error, user decides |

### Final report

After the loop ends, write `quality_reports/proposal_review_[sanitized_name]_FINAL.md`:

```markdown
# Final Review: [Proposal Title]

**Rounds:** N
**Verdict:** APPROVED | HALTED (max rounds) | HALTED (user override) | ROLLED BACK
**Token cost estimate:** ~XXk

## Round Summary
| Round | Major Concerns | Fatal Objections | Status |
|---|---|---|---|
| 1 | 7 | 2 | Fixed 5, deferred 2 |
| 2 | 3 | 1 | ...              |
| ... | ... | ... | ...         |
| N | 0 | 0 | APPROVED        |

## Changes Applied
[link to git diff between the pre-round-1 snapshot and HEAD]

## Remaining Concerns (if HALTED)
[list with severity + rationale]

## Next Steps
[recommended action: submit / one more pass / substantial revision]
```

### When NOT to use adversarial mode

- Early exploratory drafts (the loop forces premature polish on ideas still being shaped)
- Proposals you don't yet have compilable source for (can't verify edits)
- When you'd rather get ONE opinion and decide for yourself (adversarial-mode enforces "critic signed off" semantics — that's sometimes the wrong frame)

---

## `--panel [funder]` workflow detail

### Phase 0: Pre-flight

**Prior-art-probe Post-Flight.** The program officer's prior-art probe uses `WebSearch` to check whether the proposal's central idea has been done before. WebSearch results can be hallucinated — fabricated prior work, misattributed findings, wrong years. Before the program officer's desk review incorporates prior-art-probe claims into its decision, those claims must pass Post-Flight Verification per [`.claude/rules/post-flight-verification.md`](../../rules/post-flight-verification.md):

1. The program officer collects prior-art-probe claims (e.g., "Smith 2022 already funded/published this exact idea").
2. Spawn `claim-verifier` via `Task` with `subagent_type=claim-verifier` and `context=fork`, passing the claims + verification questions + candidate source URLs. Forked fresh context is the CoVe independence trick.
3. Only verified claims are allowed into the desk-review narrative. Unverified claims are surfaced separately as "program officer could not verify — manual check recommended" rather than presented as established prior work.

Opt-out: `--no-novelty-check` already skips the probe entirely. If the probe runs, Post-Flight is mandatory.

**Pre-Flight Report (required before Phase 1).** Before spawning the program officer, output a Pre-Flight Report so the user can verify the inputs are read correctly:

```markdown
## Pre-Flight Report — /review-proposal --panel

**Proposal:** [path] — [page count, last modified]
**Target funder:** [FUNDER_SHORT] → [full name from `.claude/references/funder-profiles.md`]
**Funder profile loaded:** [yes/no; resolved from `.claude/references/funder-profiles.md`; key adjustments: e.g., "Approach & Feasibility 25 → 30"]
**Round:** [fresh / r2 / r3 / stress]
```

If the proposal path doesn't exist or the target funder isn't in `.claude/references/funder-profiles.md`, stop and surface the issue before proceeding.

### Phase 1: Program-officer desk review

Spawn forked subagent `editor` with the proposal path and `--panel <FUNDER>` context. The program officer:
- Reads funder profile from `.claude/references/funder-profiles.md` → states "Calibrated to: [funder]".
- Reads abstract / specific aims + significance + approach overview + budget/timeline headline.
- Runs prior-art probes (unless `--no-novelty-check`).
- Either **DESK REJECT** (pipeline terminates with decline letter) or **SEND OUT**.

Report: `quality_reports/panel_review_[proposal]/desk_review.md`.

### Phase 1b: Panelist selection (inside program officer)

Program officer draws 2 DIFFERENT dispositions from funder's Panelist-pool weights and assigns each panelist 1 critical + 1 constructive peeve (stress mode: 2 critical + 1 constructive). Appended to `desk_review.md`.

### Phase 2: Two parallel panelists, blind to each other

Spawn in parallel:
- Forked subagent `domain-referee` with disposition D1, peeves P1 → `panelist_domain.md`.
- Forked subagent `methods-referee` with disposition D2, peeves P2 → `panelist_methods.md`.

Each panelist must include "What would change my mind: [specific ask]" on every MAJOR concern.

### Phase 3: Program-officer synthesis

Read both panelist reports. Classify each MAJOR concern as FATAL / ADDRESSABLE / TASTE. Produce funding decision using the decision rule table in `editor.md`.

Report: `quality_reports/panel_review_[proposal]/funding_decision.md`.

### Phase 4: Summary

Tell the user:
- Final decision (FUND / REVISE / DECLINE / Desk Reject)
- Token usage + wall-clock time
- Paths to all 4 reports (desk_review, panelist_domain, panelist_methods, funding_decision)

---

## Output layout for `--panel` mode

```
quality_reports/
  panel_review_[sanitized_proposal_name]/
    desk_review.md                       # Phase 1 + Phase 1b
    panelist_domain.md                   # Phase 2 (parallel)
    panelist_methods.md                  # Phase 2 (parallel)
    funding_decision.md                  # Phase 3
    (resubmission rounds: desk_review_r2.md, panelist_domain_r2.md, ...)
```

---

## Field adaptation

The shipped `funder-profiles.md` covers a generic scientific grant program (`GENERIC`, the default) plus stub profiles for `NIH`, `NSF`, and `ERC`. For another funder (a specific foundation, agency, or program), copy the profile template at the end of `funder-profiles.md` into a new section and fill in the schema. See the "Field adaptation" section there for detailed guidance. The pipeline itself is funder-agnostic; only the calibration data changes.

For a different proposal-type taxonomy in `methods-referee.md`, extend the proposal-type list (this repo's default is `grant-proposal`).
