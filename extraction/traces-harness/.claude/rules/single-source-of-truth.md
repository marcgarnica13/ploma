---
paths:
  - "manuscript/**/*"
  - "src/**/*.py"
---

# Single Source of Truth: Enforcement Protocol

**Each artifact has one authoritative source. Everything else is derived — never edit a derived
artifact independently; always propagate from the source.**

## The SSOT Chain

```
src/ pipeline (SOURCE OF TRUTH for results)
  ├── src/results/<run>/metrics.json, *.csv      → reported numbers (derived)
  └── src/results/<run>/*.png/*.svg (via save_image) → pitch figures (derived)

manuscript/samplepaper.tex (SOURCE OF TRUTH for the paper)
  ├── manuscript/fig1-5.pdf                       → included figures (derived from a pipeline run)
  ├── manuscript/mybib.bib                        → the one bibliography (shared)
  └── manuscript/samplepaper.pdf                  → compiled output (derived via `make`)

NEVER hand-edit a reported number or a figure in the paper to "match" without re-running the pipeline.
ALWAYS regenerate derived artifacts from their source.
```

---

## Results Freshness Protocol (MANDATORY)

**Before citing any number or figure in the manuscript, verify it matches the current pipeline output.**

1. Identify the result dir under `src/results/` whose config matches the paper's claim (data source, dependency threshold).
2. Read the metric from the source output (`metrics.json` / CSV), not from memory.
3. Compare against the value/figure in the manuscript.
4. If they differ beyond tolerance (see `replication-protocol.md`): re-run the pipeline and update the manuscript, or correct the manuscript — do not silently leave the drift.

### When to re-run / re-check

- The pipeline code (`src/sports_pm/**`) changed since the figures were produced.
- The Mongo data snapshot changed.
- Any reproducibility issue is reported (`/audit-reproducibility` FAIL).
- Before any commit that touches both the manuscript and the pipeline.

---

## Bibliography Parity (MANDATORY)

**`manuscript/mybib.bib` is the one bibliography.** Every `\cite{...}` key in `manuscript/*.tex` must
resolve to an entry in `mybib.bib`; no per-section `.bib` files.

---

## Content Fidelity Checklist

```
[ ] Every reported metric in the paper traces to a value in src/results/<run>/
[ ] Every figure (fig1-5.pdf) traces to a pipeline run with the stated config
[ ] Every \cite key has an entry in mybib.bib
[ ] Numbers in abstract/intro match the results section
[ ] No number hand-edited to "match" without a pipeline re-run
[ ] Pitch orientation / zone legend consistent between code output and the paper figure
```
