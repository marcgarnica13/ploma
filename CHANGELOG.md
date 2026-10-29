# Changelog

## 0.1.0-m1 (unreleased)

- Config: `ploma.yaml` schema, loader with `ploma.d/` overrides, YAML fallback parser.
- State and gate: lifecycle state, gate entries keyed to file hashes, override streak with a hard stop after three.
- Skills: onboard, doctor, status, help, compile, validate-bib, each with an eval case.
- Scripts: inventory, profiles, project files, doctor, state, gate, receipt, compile with log triage and page budget, bib check, citation lookup, validate-bib.
- Hooks: session context, subagent context, pre-compact, context monitor, verify reminder, log reminder; fail-open and silent without `ploma.yaml`.
- Rules: eager core, style and limits; reference rules.
- Venue profiles (8) and discipline profiles (3).
- Templates for project files: CLAUDE.md section, rules, reports README, learnings, status line.

## 0.1.0 (unreleased)

- Plugin skeleton: manifest, marketplace entry, manifest tests, CI.
