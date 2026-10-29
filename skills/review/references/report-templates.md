# Review report formats

## The six review dimensions

Every default-mode and adversarial report evaluates these, in this order, and rates each from 1 to 5. Method and evaluation are judged against the discipline card: identify the paper type from its `paper_types` (start from `default_paper_type`) and use that type's `sanity_checks` as the checklist.

### 1. Argument Structure
- Is the research question stated clearly, and early?
- Does the introduction motivate it?
- Does the logic flow from question to method to results to conclusion?
- Are the conclusions supported by the evidence shown?
- Are the limitations acknowledged?

### 2. Method Soundness
- Is the method described clearly enough to reimplement from the text alone?
- Are the main modeling or design choices justified rather than arbitrary or convenient?
- Are reasonable alternative choices considered?
- Does the method meet the card's `sanity_checks` for this paper type? Name each check that fails, with the quote or the missing statement.

### 3. Evaluation & Validity
- Is the headline result measured on data separate from the data used to build or tune the method? Any leakage?
- Are there baselines or controls, and ablations that isolate each design choice?
- Is the metric appropriate for the claim, and is a value of it interpreted, not just reported?
- Is uncertainty or variation reported alongside point estimates?
- Does the result generalize as far as the paper claims (other samples, periods, populations, data sources)?
- The card's `sanity_checks` on comparison, variability and reproducibility apply here; a FAIL is a major concern.

### 4. Literature Positioning
- Are the key works cited, and characterized accurately?
- Is the contribution clearly separated from prior work?
- Which missing citation would a referee flag?

### 5. Writing Quality
- Clarity and concision; academic tone.
- Consistent notation and terminology (the style block and the card's `method_conventions`).
- Does the abstract summarize the paper faithfully?

### 6. Presentation
- Tables and figures self-contained: caption, labels, units, sample size, notes.
- Typos, grammar and formatting problems visible in the PDF.
- Length proportionate to the contribution; the venue's `format_rules` respected.

## Default report

File `<outputs.dir>/paper_review_<slug>_round<N>.md`. Header from `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/report-header.md`, title "Manuscript Review". Then:

```markdown
## Summary Assessment

**Overall recommendation:** Accept | Minor revision | Revise & Resubmit | Reject

<two or three paragraphs: the contribution, the main strengths, the concerns that hold the paper back and whether they are addressable>

## Strengths

1. <specific strength, with where it shows>

## Major Concerns

### MC1: <title>
- **Location:** <file:line or section, table, figure>
- **Current:** "<verbatim span from the manuscript>"
- **Fix:** <how to address it; for an analysis, what would settle it>
- **Severity:** CRITICAL | MAJOR
- **Dimension:** <one of the six>
- **Issue:** <what is wrong and why a referee would care>

## Minor Concerns

### mc1: <title>
- **Location:** ...
- **Current:** "..."
- **Fix:** ...
- **Severity:** MINOR

## Referee Objections

### RO1: <the question a referee would ask>
**Why it matters:** <why it could sink the paper> (mark **fatal** when, unanswered, it would mean rejection)
**How to address it:** <the analysis, framing or evidence that answers it; cross-reference MC numbers>

## Summary Statistics

| Dimension | Rating (1-5) |
|---|---|
| Argument Structure | |
| Method Soundness | |
| Evaluation & Validity | |
| Literature Positioning | |
| Writing Quality | |
| Presentation | |
| **Overall** | |

## Dropped findings (quote not found)

| Finding | Quoted span as given |
|---|---|
```

Principles: be constructive (every criticism carries a fix), be specific (sections, equations, tables, lines), think like a referee at the configured venue (its `bar` and `typical_concerns`), separate fatal flaws from polish, acknowledge what is done well, and never invent a detail: if a passage cannot be read clearly, say so.

## Pre-Flight Report (`--peer`)

Printed in the reply before spawning any agent, and also when the run stops in pre-flight:

```markdown
## Pre-Flight Report: /ploma:review --peer <key> <flags>

**Manuscript:** <path> and N inputs; <pages> pages (last compile) or "page count unknown"; last modified <date>
**Venue:** <key> -> <name> (<kind>; project override | shipped profile) | NOT FOUND: '<key>'; available keys: <keys from profiles.py>
**Venue calibration:** bar: <one line>; referee pool: <dispositions with weights>; adjustments: <for example "evaluation 30 -> 35">
**Discipline:** <key> (default paper type <type>)
**Round:** fresh | r<N> (prior files: <list>) | stress | variance N
**Novelty check:** ON | OFF (--no-novelty-check)
**Cross-artifact:** PASS | FAIL, k of m claims within tolerance (<audit report path>) | skipped: pipeline off | skipped: --no-cross-artifact | skipped: no pipeline signal | not run: stopped earlier
**Next:** spawning the editor | stopped: <reason>
```

Page count: the `pages` field of the compile entry in `<outputs.dir>/verdicts/commit-gate.json` when it exists, else `pdfinfo <build.pdf>` when the PDF exists, else "page count unknown".

## Cross-artifact section

When the reproducibility audit ran (default, adversarial and seven-pass modes), the report opens, after the header, with the section of `${CLAUDE_PLUGIN_ROOT}/rules/reference/cross-artifact-review.md`: the audit verdict, k of m claims within tolerance, the audit report path, and a table of the critical manuscript and code issues. A tolerance FAIL is also a CRITICAL major concern.
