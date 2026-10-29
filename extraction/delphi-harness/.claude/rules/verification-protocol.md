---
paths:
  - "proposal/**/*.tex"
  - "proposal/refs.bib"
---

# Task Completion Verification Protocol

**At the end of EVERY task, Claude MUST verify the output works correctly.** This is non-negotiable.

## Phase 1 — Build both documents:
1. Compile with `cd proposal && make a4 && make slides` (per target: pdflatex → bibtex → pdflatex ×2) and check for errors.
2. Confirm both PDFs were produced and are **non-empty**: `proposal/proposal_a4.pdf` and `proposal/proposal_slides.pdf` exist with non-zero size.
3. Open the PDFs to verify they render: `xdg-open proposal/proposal_a4.pdf` and `xdg-open proposal/proposal_slides.pdf` (Linux).

## Phase 2 — Check outputs against compliance:
1. Parse the logs (`proposal/proposal_a4.log`, `proposal/proposal_slides.log`) for overfull/underfull hbox, undefined citations/references, and "Label(s) may have changed" (re-run `make` if present).
2. Check **page/section-limit compliance** against the funder profile (`references/funder-profiles.md`) — A4 page count within the limit, required sections present.
3. Verify all **figures exist** and render (no missing-graphic boxes in the log).
4. If the call is **blind**, confirm the PI / team identifying block remains anonymized.

## Phase 3 — Spot-check values:
1. **Budget arithmetic**: spot-check that line items sum to the stated total, and that the total is identical everywhere it appears (single source of truth).
2. **Budget ↔ timeline**: personnel effort and milestones in the narrative match the budget table and the timeline.
3. **A4 ↔ slides consistency**: headline numbers (aims, budget, timeline, dates) match across both documents — no contradictions.

## Common Pitfalls:
- **Assuming success**: always verify both PDFs exist AND contain correct content.
- **Over the page limit**: a clean compile can still bust the funder's page cap — check it.
- **Budget drift**: a number edited in one place but not another, or line items that don't sum to the total.
- **A4/slides contradiction**: the deck says one budget/timeline, the A4 another.
- **Stale figures**: content changed but the figure wasn't regenerated.
- **Accidental de-anonymization** under a blind call.

## Verification Checklist:
```
[ ] Both PDFs built successfully (non-zero size)
[ ] No compilation errors; no undefined citations / references
[ ] Within funder page / section limit; required sections present
[ ] Figures render (no missing-graphic warnings)
[ ] Budget line items sum to the total; total consistent everywhere
[ ] Budget consistent with the timeline / milestones
[ ] A4 and slides content-consistent (no contradictory numbers)
[ ] Anonymization intact (if blind review)
[ ] Reported results to user
```
