---
paths:
  - "manuscript/**/*.tex"
  - "src/**/*.py"
---

# Quality Review & Scoring Rubrics

> **Framing:** Thresholds are **advisory at the harness level**. The `/commit` skill runs a quality gate and halts on failure until the user fixes or explicitly overrides. There is no git pre-commit hook that blocks a direct `git commit` — if you bypass the skill, you bypass the review. "Gate" in this file means "checkpoint enforced by a specific skill," not "repo-wide block."

## Thresholds

- **80/100 = Commit** -- good enough to save
- **90/100 = PR** -- ready for deployment
- **95/100 = Excellence** -- aspirational

## Manuscript (manuscript/*.tex)

| Severity | Issue | Deduction |
|----------|-------|-----------|
| Critical | pdflatex compilation failure (`make`) | -100 |
| Critical | Undefined citation | -15 |
| Critical | Overfull hbox > 10pt | -10 |
| Critical | Typo in equation / metric | -10 |
| Major | Notation / terminology inconsistency | -3 |
| Major | Figure without pitch orientation / zone legend | -5 |
| Minor | Long lines / minor style | -1 |

## Python Pipeline (src/**/*.py)

| Severity | Issue | Deduction |
|----------|-------|-----------|
| Critical | Syntax / import error | -100 |
| Critical | Project-gotcha break (TAGS_FILE import, `##` key, coordinate flip, env contract) | -30 |
| Critical | Hardcoded absolute paths / credentials | -20 |
| Major | Unseeded stochastic step (no determinism statement) | -10 |
| Major | Silent empty result on Mongo failure | -10 |
| Major | Unpinned new dependency | -5 |

## Enforcement (by the /commit skill only)

- **Score < 80:** Halt within `/commit`. List blocking issues. User may override with an explicit natural-language signal ("commit anyway" / "skip quality gate") and a reason — the override is logged in the commit body.
- **Score < 90:** Allow commit within `/commit`, warn. List recommendations.
- **Direct `git commit`** (bypassing the skill): no enforcement.

## Quality Reports

Generated at review/merge time. Save to `quality_reports/merges/YYYY-MM-DD_[branch-name].md`.

## Tolerance Thresholds (Reproduction)

See `replication-protocol.md` for the authoritative tolerance contract. Summary:

| Quantity | Tolerance | Rationale |
|----------|-----------|-----------|
| Integer counts (possessions, cases) | exact (same Mongo snapshot) | no reason to differ |
| Metric values (fitness) | < 0.01 | display rounding |
| Aggregate / generalization scores | < 0.02 | pm4py internals |
