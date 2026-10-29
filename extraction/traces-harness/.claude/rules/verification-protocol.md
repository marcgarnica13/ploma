---
paths:
  - "manuscript/**/*.tex"
  - "src/**/*.py"
---

# Task Completion Verification Protocol

**At the end of EVERY task, Claude MUST verify the output works correctly.** This is non-negotiable.

## For the Manuscript (manuscript/*.tex):
1. Compile with `cd manuscript && make` (pdflatex → bibtex → pdflatex ×2) and check for errors.
2. Open the PDF to verify figures render: `xdg-open manuscript/samplepaper.pdf` (Linux).
3. Parse `manuscript/samplepaper.log` for overfull hbox, undefined citations/references, and "Label(s) may have changed" (re-run `make` if present).
4. Confirm authors remain anonymized unless a non-blind submission was explicitly requested.

## For Python Pipeline Scripts (src/**/*.py):
1. Run from `src/` with the env-var contract set (export `TAGS_FILE` before importing the parser):
   `uv run python notebooks/discovery/parse_statsbomb_matches.py`.
2. Verify output files (metrics JSON/CSV, figures) were created in `src/results/<run>/` with non-zero size.
3. Spot-check metrics for reasonable magnitude (e.g., fitness in [0, 1]); confirm node names still contain `##`.
4. Confirm the run did not silently produce empty results (e.g., on a Mongo failure).

## For Pitch Figures:
1. Verify figure files are valid (non-zero, openable) and exported via `save_image`.
2. Check pitch orientation and the zone legend — a mirrored pitch is a correctness bug.

## Common Pitfalls:
- **Assuming success**: always verify output files exist AND contain correct content.
- **Import-time crash**: `TAGS_FILE` not exported before importing the parser.
- **Mirrored pitch**: forgotten/double coordinate flip.
- **Silent empty results**: Mongo unreachable but the script "succeeded".
- **Stale figures**: pipeline changed but `fig1-5.pdf` in the manuscript wasn't regenerated.

## Verification Checklist:
```
[ ] Output file(s) created successfully (non-zero)
[ ] No compilation / runtime errors
[ ] Manuscript: pdflatex clean, no undefined citations, figures render
[ ] Pipeline: metrics in expected range, node names contain `##`, no silent empty results
[ ] Pitch orientation / zone legend correct
[ ] Reported results to user
```
