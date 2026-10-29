---
paths:
  - "proposal/**/*.tex"
  - "proposal/refs.bib"
---

# Content Invariants (INV-1 through INV-12)

Numbered non-negotiable rules for content produced in this repository. Critic agents, reviewers, and review agents should cite invariants by number (e.g., "violates INV-3") when flagging issues.

## Build & document invariants

- **INV-1: pdflatex build only.** The proposal builds via `cd proposal && make` (per target: pdflatex → bibtex → pdflatex ×2). Never introduce xelatex/lualatex-only constructs. The `proposal/` folder must stay self-contained (class/style files, `refs.bib`, figures all inside it) so it also compiles on Overleaf.
- **INV-2: Single bibliography.** `proposal/refs.bib` is the canonical bibliography for both documents. No per-section `.bib` files. Every `\cite{...}` must resolve against this one file — no undefined citations.
- **INV-3: Blind-review anonymization (when the funder requires it).** If the call is blind, the PI / team identifying block stays anonymized. Do not un-anonymize unless preparing a non-blind submission.

## Proposal-content invariants

- **INV-4: Concrete, testable specific aims.** Each specific aim states a concrete objective with a verifiable success criterion (a deliverable, a measurable outcome, or a decision point). No vague aspiration presented as an aim.
- **INV-5: Explicit scope boundaries.** What the project will and will *not* do is stated explicitly. Out-of-scope items and known limitations are named, not implied.
- **INV-6: Every claim traceable.** Every factual or quantitative claim is backed by a citation (resolving against `refs.bib`) or by a clearly stated assumption. No unsupported assertion stands as evidence.
- **INV-7: Related-work completeness.** The proposal positions itself against the relevant prior and competing work; key competing approaches are cited and distinguished. A missing obvious competitor is a content bug.
- **INV-8: Significance & innovation stated up front.** The significance (why it matters) and the innovation (what is new) are each statable in one paragraph. No unmotivated method — every methodological choice is justified before it is relied upon.

## Budget, timeline & compliance invariants

- **INV-9: Single source of truth for budget.** Budget totals are pinned to one canonical source. No hand-edited copies that can drift; line items must sum to the stated total wherever the total appears.
- **INV-10: Budget ↔ timeline consistency.** The budget and the project timeline are mutually consistent — personnel effort, milestones, and costs line up across the budget table, the Gantt/timeline, and the narrative.
- **INV-11: Funder formatting & page-limit compliance.** The document respects the funder's page limit, section structure, font/margin rules, and any required sections (see `references/funder-profiles.md`). Exceeding the page/section limit is a critical bug, not cosmetic.
- **INV-12: A4 ↔ slides content consistency.** The formal A4 proposal and the slide deck must not contradict each other — aims, budget figures, timeline, and headline numbers must match across both. Notation/terminology defined one way keeps that meaning throughout both documents; drift is a critical bug.
