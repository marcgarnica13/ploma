---
name: proofread
description: Read-only proofreading pass over the proposal `.tex` files. Checks grammar, typos, overflow, terminology consistency, and academic writing quality; produces a report without editing. Use when user says "proofread", "check for typos", "look for grammar issues", "copy-edit this", "any writing errors?", or before submission.
argument-hint: "[filename or 'all'] (defaults to proposal/*.tex)"
allowed-tools: ["Read", "Grep", "Glob", "Write", "Task"]
---

# Proofread the Proposal

Run the mandatory proofreading protocol on the proposal. This produces a report of all issues found WITHOUT editing any source files.

## Steps

1. **Identify files to review:**
   - If `$ARGUMENTS` is a specific filename: review that file only
   - If `$ARGUMENTS` is "all" (or empty): review the proposal `.tex` files in `proposal/` (default both `proposal/proposal_a4.tex` and `proposal/proposal_slides.tex`)

2. **For each file, launch the proofreader agent** that checks for:

   **GRAMMAR:** Subject-verb agreement, articles (a/an/the), prepositions, tense consistency
   **TYPOS:** Misspellings, search-and-replace artifacts, duplicated words
   **OVERFLOW:** Overfull hbox (pdflatex log; check both A4 and slides logs)
   **CONSISTENCY:** Citation format (`\cite{...}`), notation, terminology (e.g. "aim", "objective", "work package", "milestone")
   **ACADEMIC QUALITY:** Informal language, missing words, awkward constructions

3. **Produce a detailed report** for each file listing every finding with:
   - Location (line number or section title)
   - Current text (what's wrong)
   - Proposed fix (what it should be)
   - Category and severity

4. **Save each report** to `quality_reports/`:
   - `quality_reports/FILENAME_report.md`

5. **IMPORTANT: Do NOT edit any source files.**
   Only produce the report. Fixes are applied separately after user review.

6. **Present summary** to the user:
   - Total issues found per file
   - Breakdown by category
   - Most critical issues highlighted
