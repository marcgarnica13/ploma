---
name: compile-latex
description: Compile the manuscript LaTeX paper with pdflatex via the Makefile (pdflatex -> bibtex -> pdflatex x2). Use when user says "compile", "build the paper", "rebuild the PDF", "run latex", "render the tex", or asks why `samplepaper.tex` isn't producing a PDF. Operates on `manuscript/samplepaper.tex`.
argument-hint: "(no args; builds manuscript/samplepaper.tex)"
allowed-tools: ["Read", "Bash", "Glob"]
---

# Compile the Manuscript (pdflatex)

Compile the Springer LLNCS paper using the project's `make` build, with full citation resolution.

## Steps

1. **Build via the Makefile** (run from `manuscript/`). This runs the required 4-step sequence
   (`pdflatex` -> `bibtex` -> `pdflatex` x2):

```bash
cd manuscript && make
```

The Makefile's first pass is `pdflatex -interaction=nonstopmode -halt-on-error samplepaper.tex`,
then `bibtex samplepaper`, then two more `pdflatex` passes. Output: `manuscript/samplepaper.pdf`.

   Cleaning targets, if needed:
   ```bash
   cd manuscript && make clean      # remove LaTeX aux files, keep the PDF
   cd manuscript && make cleanall   # also remove samplepaper.pdf
   ```

2. **Check the log for warnings.** Parse `manuscript/samplepaper.log`:
   - `Overfull \hbox` (line-breaking / margin overflows)
   - `LaTeX Warning: Citation ... undefined` (missing bib entry or stale `.aux` — usually fixed by
     a full `make`, which re-runs bibtex)
   - `LaTeX Warning: Reference ... undefined`
   - `Label(s) may have changed. Rerun to get cross-references right.` (cross-refs not yet stable)

   ```bash
   grep -nE "Overfull \\\\hbox|Citation .* undefined|Reference .* undefined|Label\(s\) may have changed" manuscript/samplepaper.log
   ```

3. **Open the PDF** for visual verification (Linux):
   ```bash
   xdg-open manuscript/samplepaper.pdf
   ```

4. **Report results:**
   - Compilation success/failure (non-zero exit from `make`, or a `! ` fatal error in the log)
   - Number of overfull hbox warnings
   - Any undefined citations / references
   - Whether a "Label(s) may have changed" warning remains (if so, `make` again)
   - PDF page count

## Why the 4-step build?
1. First `pdflatex`: creates the `.aux` file with citation keys and labels
2. `bibtex`: reads the `.aux`, generates `.bbl` with formatted references (uses `splncs04.bst`)
3. Second `pdflatex`: incorporates the bibliography
4. Third `pdflatex`: resolves all cross-references with final page numbers

## Important
- **Use pdflatex (via `make`), never xelatex.** The paper uses the Springer LLNCS class
  (`llncs.cls`) with `splncs04.bst`; the build is self-contained in `manuscript/`.
- The manuscript folder is self-contained (class/style files, `mybib.bib`, `fig1-5.pdf` all live
  there) and also compiles on Overleaf with `samplepaper.tex` as the main document.
- Authors are intentionally **anonymized** in `samplepaper.tex` (real author block commented out) —
  do not un-anonymize unless preparing a non-blind submission.
