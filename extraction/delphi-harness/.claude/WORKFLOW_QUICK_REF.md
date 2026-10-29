# Workflow Quick Reference

**Model:** Contractor (you direct, Claude orchestrates)

---

## The Loop

```
Your instruction
    ↓
[PLAN] (if multi-file or unclear) → Show plan → Your approval
    ↓
[EXECUTE] Implement, verify, done
    ↓
[REPORT] Summary + what's ready
    ↓
Repeat
```

---

## I Ask You When

- **Design forks:** "Option A (lean budget) vs. Option B (broader scope). Which?"
- **Content ambiguity:** "Aim 3's success criterion is unstated. Assume X?"
- **Compliance edge case:** "This section pushes us over the page limit. Cut or condense?"
- **Scope question:** "Also draft the broader-impact section while here, or focus on the aims?"

---

## I Just Execute When

- A fix is obvious (typo, undefined citation, formatting correction)
- Verification (page-limit check, budget arithmetic, pdflatex build of A4 + slides)
- Documentation (logs, commits)
- Figures (per established standards)

---

## Quality Gates (No Exceptions)

| Score | Action |
|-------|--------|
| >= 80 | Ready to commit |
| < 80  | Fix blocking issues |

See `.claude/rules/quality-gates.md`.

---

## Non-Negotiables (this project's locked conventions)

- **Cite funder requirements / eligibility in the aims.** The specific aims and approach must be
  written against the call's stated requirements and eligibility (see `references/funder-profiles.md`).
- **Pin budget totals to a single source.** No hand-edited copies of the budget — line items sum to
  the total, and the total reads identically everywhere it appears.
- **Keep A4 and slides content-consistent.** `proposal/proposal_a4.tex` and
  `proposal/proposal_slides.tex` must not contradict each other on aims, budget, timeline, or
  headline numbers.
- **Build via `cd proposal && make all`** (per target: pdflatex → bibtex → pdflatex ×2, **not
  xelatex**). Outputs: `proposal/proposal_a4.pdf` and `proposal/proposal_slides.pdf`.
- **Respect the funder page / section limit and format.** A clean compile that busts the page cap is
  a failure.
- **Keep the PI / team block anonymized** if the funder requires blind review.
- **Single bibliography.** All citations resolve against `proposal/refs.bib`; no undefined citations.

---

## Preferences

<!-- Fill in as you discover your working style -->

**Visual:** [How you want figures / slides handled]
**Reporting:** [Concise bullets? Detailed prose? Details on request?]
**Session logs:** Always (post-plan, incremental, end-of-session)
**Compliance:** [How strict on page limits? Flag near-misses early?]

---

## Exploration Mode

For experimental / draft work, use the **Fast-Track** workflow:
- Work in `drafts/` folder
- 60/100 quality threshold (vs. 80/100 for production)
- No plan needed — just a value check (2 min)
- See `.claude/rules/exploration-fast-track.md`

---

## Next Step

You provide task → I plan (if needed) → Your approval → Execute → Done.
