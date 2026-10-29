---
paths:
  - "manuscript/**/*.tex"
  - "manuscript/mybib.bib"
  - "src/**/*.py"
  - "src/sports_pm/**/*.py"
---

# Content Invariants (INV-1 through INV-12)

Numbered non-negotiable rules for content produced in this repository. Critic agents, reviewers, and audit agents should cite invariants by number (e.g., "violates INV-3") when flagging issues. Adapted from clo-author's enforcement pattern.

## Manuscript invariants

- **INV-1: pdflatex build only.** The paper builds via `cd manuscript && make` (pdflatex → bibtex → pdflatex ×2). Never introduce xelatex/lualatex-only constructs. The `manuscript/` folder must stay self-contained (class/style files, `mybib.bib`, `fig1-5.pdf` all inside it) so it also compiles on Overleaf.
- **INV-2: Springer LLNCS class.** The paper uses `llncs.cls` with `splncs04.bst`. Do not switch document class or bibliography style without an explicit instruction; citations are `\cite{...}`.
- **INV-3: Authors anonymized until non-blind.** The real author block in `samplepaper.tex` stays commented out (blind submission). Do not un-anonymize unless preparing a non-blind submission.
- **INV-4: Figures are PDF, self-contained.** Manuscript figures (`fig1-5.pdf`) are included as PDF and must read standalone — caption, pitch orientation, and zone legend present. A mirrored pitch (wrong coordinate orientation) is a content bug, not a cosmetic one.
- **INV-5: Single bibliography.** `manuscript/mybib.bib` is the canonical bibliography. No per-section `.bib` files. All citations must resolve against this one file.

## Presentation invariants

- **INV-6: Clarity of contribution.** The ML-general contribution must be statable in one paragraph in the introduction. No unmotivated method — every methodological choice (segmentation rule, 24-zone abstraction, `action##zone` activity key, dependency threshold) is motivated before it is used.
- **INV-7: Notation consistency.** A symbol/term defined one way (e.g., "zone", "action", "possession", "fitness") keeps that meaning throughout. Notation drift between sections is a critical bug.
- **INV-8: Honest evaluation framing.** Reported metrics must be presented with the evaluation regime they were measured under (held-out vs fit-on-train). No metric presented as evidence of generalization unless measured out-of-sample.

## Python pipeline invariants

- **INV-9: Determinism / seeding.** Any pipeline step that uses randomness (sampling, stochastic discovery, sweeps) must be seeded once, or be documented as deterministic. No unseeded stochastic results behind a reported number.
- **INV-10: No hard-coded paths or credentials.** No absolute paths (`/home/...`, `C:\...`) and no inline Mongo credentials. Use the env-var contract (`MONGO_*`, `TAGS_FILE`, `RESULTS_FILE`) and route outputs through `viz/image_utils.save_image` / `RESULTS_FILE`. Run scripts from `src/`.
- **INV-11: `action##zone` activity-key format.** `create_event_log` emits activities as `"{action_id|sub_action_id}##{key_zone}"`; consumers split on `"##"`. The format is invariant — do not change the delimiter or field order.
- **INV-12: Standardized-space zoning + orientation.** Zone assignment (`get_zone_id`) runs on standardized 105×68 coordinates (`get_standard_positions` / `..._from_statsbomb`), never raw coordinates, and coordinate orientation (the `y -> FIELD_WIDTH - y` flip, attacking-direction normalization) must be consistent end-to-end.
