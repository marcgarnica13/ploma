# Paper spec template

`/ploma:spec` writes `<outputs.dir>/paper_spec.md` from this template. The spec is the binding contract `/ploma:write --from-spec` drafts against: change the file, not the chat. Every placeholder is replaced or the row is removed; an unknown value is an entry under Open questions, never a guess.

Evidence pointers take one of three forms: `file:line` in the manuscript (checked with Grep), a results key as `<results file>:<key>` (for example `results/metrics.json:avg_fitness`), or `planned: <experiment>` for evidence that does not exist yet.

```markdown
# Paper Spec: <working title>

**Status:** binding contract for /ploma:write
**Created:** <YYYY-MM-DD>
**Updated:** <YYYY-MM-DD>
**Paper type:** <a paper type name from the discipline card | unsure>
**Discipline card:** <key>
**Decision log:** <outputs.dir>/decisions/<file>.md | none

## Identity

<One sentence: what the paper shows, by what means, on what evidence, for whom.>

## Venue constraints

| Constraint | Value | Source |
|---|---|---|
| Venue profile | <key>: <name> | venue.profile |
| Page budget | <N pages, references included or excluded> or none | venue.page_budget, else the profile |
| Anonymity | anonymized or not | document.anonymized, else the profile |
| Citation style | numeric or author-year | venue.cite_style |
| Document class | <class> | venue.doc_class |
| Venue bar | <one sentence from the profile's bar> | the profile |

## Claims and evidence

| ID | Claim | Evidence | Status |
|---|---|---|---|
| C1 | <one sentence> | <file:line, results file:key, or planned: experiment> | supported, planned or open |

## Evaluation plan

- **Method:** <what is run>
- **Evaluation regime:** <held-out split, cross-validation, controls; what the discipline card expects>
- **Baselines:** <each comparison and why>
- **Metrics:** <each metric, what a value means>
- **Ablations and robustness:** <which design choices are isolated>
- **Threats:** <the card's sanity checks that apply, and how each is handled>

## Positioning

| Closest work | What it does | This paper's delta | Cite key |
|---|---|---|---|
| <Author (Year)> | <one line> | <one line> | <bib key or TO VERIFY> |

## Section architecture

| Section | File | Purpose | Claims served | Target pages |
|---|---|---|---|---|
| Introduction | <path> | <one line> | C1 | <pages> |

**Total:** <sum> of <budget> pages (<references included or excluded>).

## Locked decisions

| ID | Decision | Choice | Rationale | Source |
|---|---|---|---|---|
| L1 | <decision> | <choice> | <why> | decisions/<file>.md#D1, interview <date>, or the repo (<evidence>) |

## Open questions

- **Q1:** <question>. Why it matters: <one line>. Recommended: <answer and reason>.

## Figures needed

| ID | Shows | Claim | Section | Source script |
|---|---|---|---|---|
| F1 | <what the reader sees> | C1 | <section> | `% ploma:source <script> <args>`, or unknown |

## Post-flight verification

<the output block from skills/_shared/references/cove.md>
```
