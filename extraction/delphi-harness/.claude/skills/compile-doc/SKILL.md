---
name: compile-doc
description: Compile the proposal documents with pdflatex via the Makefile (pdflatex -> bibtex -> pdflatex x2). Use when user says "compile", "build the proposal", "build the slides", "rebuild the PDF", "run latex", "render the tex", or asks why a `.tex` file isn't producing a PDF. Operates on `proposal/proposal_a4.tex` and `proposal/proposal_slides.tex`.
argument-hint: "[a4 | slides | all]  (default: all — builds both PDFs)"
allowed-tools: ["Read", "Bash", "Glob"]
---

# Compile the Proposal (pdflatex)

Compile the grant proposal documents using the project's `make` build, with full citation resolution.
Two targets exist: the formal **A4 PDF** (`proposal_a4.pdf`) and the **slide deck** (`proposal_slides.pdf`).

## Steps

1. **Build via the Makefile** (run from `proposal/`). Each target runs the required 4-step sequence
   (`pdflatex` -> `bibtex` -> `pdflatex` x2):

```bash
cd proposal && make all      # builds both PDFs (a4 + slides)
cd proposal && make a4       # formal A4 proposal only  -> proposal_a4.pdf
cd proposal && make slides   # beamer slide deck only   -> proposal_slides.pdf
```

For each target, the first pass is `pdflatex -interaction=nonstopmode -halt-on-error <target>.tex`,
then `bibtex <target>`, then two more `pdflatex` passes. Outputs: `proposal/proposal_a4.pdf` and
`proposal/proposal_slides.pdf`.

   Cleaning targets, if needed:
   ```bash
   cd proposal && make clean      # remove LaTeX aux files, keep the PDFs
   cd proposal && make cleanall   # also remove the built PDFs
   ```

2. **Check the logs for warnings.** Parse the per-target log (`proposal/proposal_a4.log`,
   `proposal/proposal_slides.log`):
   - `Overfull \hbox` / `Underfull \hbox` (line-breaking / margin overflows)
   - `LaTeX Warning: Citation ... undefined` (missing bib entry or stale `.aux` — usually fixed by
     a full `make`, which re-runs bibtex)
   - `LaTeX Warning: Reference ... undefined`
   - `Label(s) may have changed. Rerun to get cross-references right.` (cross-refs not yet stable)

   ```bash
   grep -nE "Overfull \\\\hbox|Underfull \\\\hbox|Citation .* undefined|Reference .* undefined|Label\(s\) may have changed" proposal/proposal_a4.log proposal/proposal_slides.log
   ```

3. **Open the PDFs** for visual verification (Linux):
   ```bash
   xdg-open proposal/proposal_a4.pdf
   xdg-open proposal/proposal_slides.pdf
   ```

4. **Report results, per target:**
   - Compilation success/failure (non-zero exit from `make`, or a `! ` fatal error in the log)
   - Number of overfull / underfull hbox warnings
   - Any undefined citations / references
   - Whether a "Label(s) may have changed" warning remains (if so, `make` again)
   - PDF page count (and whether it is within the funder page limit)

## Why the 4-step build (per target)?
1. First `pdflatex`: creates the `.aux` file with citation keys and labels
2. `bibtex`: reads the `.aux`, generates `.bbl` with formatted references (from `proposal/refs.bib`)
3. Second `pdflatex`: incorporates the bibliography
4. Third `pdflatex`: resolves all cross-references with final page numbers

## Important
- **Use pdflatex (via `make`), never xelatex.** The build is self-contained in `proposal/`.
- The `proposal/` folder is self-contained (class/style files, `refs.bib`, figures all live there)
  and also compiles on Overleaf with the relevant `.tex` as the main document.
- If the funder requires **blind review**, the author/PI block stays **anonymized** — do not
  un-anonymize unless preparing a non-blind submission.
- **A4 and slides share `refs.bib` and must stay content-consistent** — do not let numbers (budget,
  timeline, aims) drift between the two PDFs.
