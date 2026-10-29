# Proofreading protocol

The manuscript is proofread before any submission commit. The proofreader never applies changes; it proposes them.

## What it checks

1. Grammar: agreement, articles, prepositions.
2. Typos: misspellings, duplicated words, search-and-replace damage.
3. Overflow: overfull boxes above `build.overfull_threshold_pt` in the log at `build.log`.
4. Consistency: notation and terminology used the same way throughout; one citation style (`venue.cite_style`).
5. Academic quality: informal abbreviations, missing words, awkward phrasing, the style rule's forbidden phrases.

## Three phases

### Phase 1: review and propose (no edits)

The `ploma:proofreader` agent reads each file in full and returns a report that `/ploma:proofread` writes to `<outputs.dir>/<stem>_report.md` (one per file; `<stem>` is the file name without `.tex`). Every proposed change carries location (file:line or section), current text, proposed fix and category. No source file is modified.

### Phase 2: approval

The user accepts all, accepts some, or asks for changes. Nothing proceeds without explicit approval.

### Phase 3: apply

Apply only the approved changes, one edit per finding, and confirm each edit. Then recommend `/ploma:compile` and record the gate entry through `/ploma:proofread`.
