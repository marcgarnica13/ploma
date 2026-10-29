# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with this repository.

## What this is

**`delphi_nba`** is a **scientific grant application** — a proposal writing project, not a
software project. There is no code pipeline and no dataset here: the deliverable is a funded
proposal. The repository holds the **proposal sources** (`proposal/`), a **Claude Code harness**
(`.claude/`) tuned for grant writing, and the **working artifacts** (plans, specs, session logs,
quality reports) that the harness produces.

The proposal is authored once in LaTeX and built into **two PDF outputs**:

- a **formal A4 document** (`proposal/proposal_a4.tex` → `proposal_a4.pdf`), and
- a **slide-deck pitch** (`proposal/proposal_slides.tex` → `proposal_slides.pdf`, beamer).

Both share one bibliography (`proposal/refs.bib`) and **must stay content-consistent** — the same
aims, budget figures, and timeline appear in both (see `.claude/rules/content-invariants.md`).

## Repository layout

| Path | What it is | How to operate it |
|------|------------|-------------------|
| `proposal/` | LaTeX sources for the proposal: `proposal_a4.tex` (A4 document), `proposal_slides.tex` (beamer deck), shared `refs.bib`, and a `Makefile`. | `cd proposal && make all`. See **Building the proposal**. |
| `templates/` | Reusable templates: requirements spec, session log, quality report, proposal content skeleton, funder-profile template. | Copy into `quality_reports/…` or `.claude/references/` as needed. |
| `quality_reports/` | Plans (`plans/`), requirement specs (`specs/`), session logs (`session_logs/`), and merge-time quality reports (`merges/`). | Written by the harness workflow; see `.claude/rules/`. |
| `drafts/` | Sandbox for exploratory writing not yet graduated into the proposal. | See `.claude/rules/exploration-folder-protocol.md`. |
| `.claude/` | The committed Claude Code harness (skills, agents, rules, references, hooks). | See **Claude Code harness**. |

## Building the proposal

The proposal needs only a LaTeX toolchain (TeX Live, with beamer).

```bash
cd proposal
make a4        # build the formal A4 PDF
make slides    # build the slide-deck PDF
make all       # build both (default)
make clean     # remove LaTeX aux files, keep PDFs
make cleanall  # also remove the built PDFs
```

Each target runs the four-step chain (`pdflatex → bibtex → pdflatex ×2`) so citations and
cross-references resolve. The `/compile-doc` skill drives this and reports overfull boxes and
undefined citations per target.

## Conventions & gotchas

- **Two outputs, one truth.** A4 and slides are separate `.tex` files; keep their aims, budget
  totals, and timeline identical. Diverging numbers are an invariant violation.
- **Single-source budget.** Budget figures live in one place and are referenced, not retyped.
- **Funder compliance.** Page/section limits and required sections are funder-specific. When a
  funder is chosen, calibrate `.claude/references/funder-profiles.md` and check compliance before
  every submission build.
- **Blind review.** If the funder requires anonymization, strip identifying author/institution
  info before submission (the author block is filled in for working drafts).
- **No code in this repo.** This is writing-only; there is no pipeline, no env-var contract, and
  no reproducibility audit.

## Claude Code harness (`.claude/`)

This repo ships a committed, grant-tuned Claude Code harness adapted from an academic-paper harness.
Two layers:

1. **superpowers** — installed once as a plugin (methodology: brainstorm → plan → review →
   git worktrees → systematic debugging). No API key.
   ```
   /plugin marketplace add obra/superpowers-marketplace
   /plugin install superpowers@superpowers-marketplace
   ```
2. **Vendored grant-writing layer** in `.claude/` — committed, adapted to a funder-agnostic grant
   application. Key slash-skills:

   | Skill | What it does here |
   |-------|-------------------|
   | `/compile-doc` | Builds `proposal/` via `make` — the A4 PDF and the slide deck — and reports overfull boxes + undefined citations per target. |
   | `/review-proposal [--panel FUNDER] [--adversarial]` | Proposal review; `--panel` runs a simulated funder panel (program officer + 2 dispositioned panelists) calibrated to a funder profile, ending in a FUND / REVISE / DECLINE decision. |
   | `/respond-to-reviewers` | Drafts a point-by-point response/rebuttal mapping a funder panel's critiques to revisions (CoVe-verified). |
   | `/validate-bib [--semantic]` | Checks `\cite` keys vs `proposal/refs.bib`; DOI verification via Crossref / Semantic Scholar / OpenAlex (free, no API key). |
   | `/lit-review`, `/research-ideation`, `/interview-me` | Literature, ideation, and idea-formalization for the proposal narrative. |
   | `/seven-pass-review`, `/deep-audit`, `/devils-advocate` | Multi-lens review, repository audit, and adversarial stress-testing of the proposal design. |
   | `/proofread`, `/verify-claims` | Writing-quality and fact-checking passes over the proposal. |

   Supporting `agents/` (program-officer `editor`, `methods-referee`, `domain-referee`,
   `domain-reviewer`, `doc-verifier`, `claim-verifier`, `proofreader`), `rules/`,
   `references/funder-profiles.md` (generic + NIH/NSF/ERC stubs), and audited `hooks/` round it out.
   `settings.json` uses conservative permissions (no `bypassPermissions`; secrets `**/.env*` denied).
   Per-user overrides go in the git-ignored `.claude/settings.local.json`.

### Workflow (plan-first)

For any non-trivial task: enter plan mode, check `MEMORY.md`, write a spec for ambiguous tasks,
save the plan to `quality_reports/plans/`, get approval, then execute. See
`.claude/rules/plan-first-workflow.md` and `.claude/WORKFLOW_QUICK_REF.md`.
