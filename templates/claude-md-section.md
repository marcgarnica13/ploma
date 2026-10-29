<!-- ploma:begin -->
## ploma

This repo uses ploma, a Claude Code plugin that runs the LaTeX paper lifecycle.

- Facts live in ploma.yaml: build, venue, style and pipeline settings. The rules under `.claude/rules/ploma-*.md` are generated from it.
- Never restate the paper's facts in CLAUDE.md. Edit ploma.yaml and re-run /ploma:onboard.
- Installed skills: /ploma:compile, /ploma:validate-bib, /ploma:audit-reproducibility, /ploma:doctor, /ploma:status, /ploma:help, /ploma:onboard.
- Planned (milestone 2), not installed yet, do not invoke: brainstorm, lit-review, grill, spec, write, format, verify-claims, proofread, review, devils-advocate, respond, commit.
- Health and position: /ploma:doctor and /ploma:status.

This section is maintained by /ploma:onboard between the ploma markers; text outside the markers is yours.
<!-- ploma:end -->
