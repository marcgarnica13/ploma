---
paths:
  - "proposal/**/*.tex"
  - "proposal/refs.bib"
---

# Quality Review & Scoring Rubrics

> **Framing:** Thresholds are **advisory at the harness level**. The `/commit` skill runs a quality gate and halts on failure until the user fixes or explicitly overrides. There is no git pre-commit hook that blocks a direct `git commit` — if you bypass the skill, you bypass the review. "Gate" in this file means "checkpoint enforced by a specific skill," not "repo-wide block."

## Thresholds

- **80/100 = Commit** -- good enough to save
- **90/100 = PR** -- ready for submission-track work
- **95/100 = Excellence** -- aspirational

## Proposal (proposal/*.tex)

| Severity | Issue | Deduction |
|----------|-------|-----------|
| Critical | pdflatex compilation failure (`make`) | -100 |
| Critical | Undefined citation | -15 |
| Critical | Over the funder page / section limit | -15 |
| Critical | Overfull hbox > 10pt | -10 |
| Critical | Budget total inconsistent across the document | -10 |
| Critical | A4 ↔ slides contradiction (aims / budget / timeline) | -10 |
| Major | Specific aim not concrete / not testable | -8 |
| Major | Significance or broader-impact statement missing / weak | -6 |
| Major | Approach not shown feasible (no plan, no risk mitigation) | -6 |
| Major | Budget not justified / not tied to timeline | -5 |
| Major | Timeline unrealistic (milestones don't fit the period) | -5 |
| Major | Notation / terminology inconsistency | -3 |
| Minor | Typo | -2 |
| Minor | Long lines / minor style | -1 |

## Scoring dimensions (grant rubric)

When scoring a proposal, weigh these dimensions:

- **Specific-aims clarity** — concrete, testable, scoped objectives.
- **Significance** — importance of the problem and the expected payoff.
- **Feasibility of approach** — methods, preliminary basis, risk mitigation.
- **Budget justification** — costs explained and tied to the work.
- **Timeline realism** — milestones fit the funding period and effort.
- **Broader-impact statement** — societal / scientific / training impact present and credible.
- **Funder compliance** — page limits, required sections, format/eligibility (see `references/funder-profiles.md`).
- **Citation hygiene** — every claim sourced; no undefined or unused citations.
- **Prose quality** — clear, direct, free of typos and overfull boxes.
- **A4 ↔ slides consistency** — headline numbers and claims match across both documents.

## Enforcement (by the /commit skill only)

- **Score < 80:** Halt within `/commit`. List blocking issues. User may override with an explicit natural-language signal ("commit anyway" / "skip quality gate") and a reason — the override is logged in the commit body.
- **Score < 90:** Allow commit within `/commit`, warn. List recommendations.
- **Direct `git commit`** (bypassing the skill): no enforcement.

## Quality Reports

Generated at review/merge time. Save to `quality_reports/merges/YYYY-MM-DD_[branch-name].md`.
