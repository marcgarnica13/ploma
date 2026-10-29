# Cut plan format

The page budget report `<outputs.dir>/page_budget_<slug>.md` follows the structure of a cut proposal an author has already accepted. It proposes; it never cuts. Every number in it comes from `scripts/page_map.py` output or is marked as an estimate (`~`).

Open with the report header (`${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/report-header.md`, title "Page Budget"), then these sections in this order. Within budget, write only the header, the measured table, the page map and a one-line verdict ("Within budget: N of B pages. No cuts needed.").

```markdown
# Page Budget: <document title>

**Date:** YYYY-MM-DD
**File:** <build.pdf>
**Skill:** /ploma:format <arguments>
**Config:** <one-line config summary>
**Status:** DRAFT, proposals only; no source file edited.
**Context:** <counted> pages counted against a budget of <B> (<rule: every page counts | references excluded, they start on page R>); over by <N>. <PDF stale note when the PDF is older than the sources.>

## Where the pages go (measured)

| Block | Pages (approx) | Counts toward the budget? |
|---|---|---|
| Body text (<words_total> words) | ~<pages if pure text> | yes |
| <figures_total> figures, <tables_total> tables (floats and float whitespace) | ~<estimate> | yes |
| References (pages R to P) | ~<P - R + 1> | yes / **no, free** |

<One or two lines naming the levers, for example: (L1) prose density and (L2) figure and float footprint.>

## Page map

| # | Section | Starts p. | Est. pages | Figures | Tables | Words |
|---|---|---|---|---|---|---|
<one row per section, from page_map.py; "not found" when the heading was not located>

## Principle

<One short paragraph. The default: compress and relocate, do not delete substance. Keep every contribution in the paper; reclaim whitespace, tighten prose, move detail (not contribution) to an appendix or online supplement when the venue allows one. State what the venue allows when the profile says so.>

## Cut plan (ordered by value per page, ~<N> pages to recover)

### A. <Lever with the best pages recovered per unit of content lost>: reclaim ~<x> pp, <content loss: none | what>
1. **<Concrete action naming the section, figure or table>** (<reason>). (~<pages> pp)
2. ...

### B. <Next lever>: ...
<Continue in descending value per page. Typical order: float footprint (merge, resize, place), then prose compression in the longest low-novelty sections (related work, discussion), then relocation of depth to an appendix or supplement, then trimming a featured section to one worked example. Each item names the section and its current estimated pages from the map.>

## Resulting budget (target <= <B>)

| Section | Now | After plan |
|---|---|---|
<one row per section: Now from est_pages, After plan after the cuts that touch it>
| **Total counted** | **<counted>** | **~<after>** |

## What is not cut

- <The contributions, the core method and evaluation, the claims the paper's spec or introduction promises, citations (they cost little).>

## Risk

- <What could go wrong with the plan: a body that no longer stands alone after relocation, a figure that becomes illegible when shrunk, estimates that are off because the map is approximate.>

## Recommendation

<One or two sentences: which blocks to execute first and the stopping point. Name the next command, for example "/ploma:write <section> to draft the compressed section as a sibling file".>
```

## Estimating pages

- A section's current pages are its `est_pages` from the map. A section whose heading was not found gets "?" and a note; never fill it in.
- A float costs roughly its height plus the whitespace around it; full-width floats in a two-column layout and floats that force a float page cost more. Say "~" for every estimate.
- Prose compression: cutting a fraction of a section's words saves about that fraction of its text pages, not of its figure pages.
- The sum of the cuts must reach the overage, or the recommendation says it does not and names the remaining options (a split, a shorter scope, a venue with more pages).
