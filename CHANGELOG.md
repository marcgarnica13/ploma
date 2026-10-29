# Changelog

## 0.1.0 (unreleased)

Note: `consistency` is a recommended gate check in 0.1.0 and becomes a required gate check in 0.1.1.

### Milestone 1: foundation

- Plugin skeleton: manifest, marketplace entry, manifest tests, CI.
- Config: `ploma.yaml` schema, loader with `ploma.d/` overrides, YAML fallback parser.
- State and gate: lifecycle state, gate entries keyed to file hashes, override streak with a hard stop after three.
- Skills: onboard, doctor, status, help, compile, validate-bib.
- Scripts: inventory, profiles, project files, doctor, state, gate, receipt, compile with log triage and page budget, bib check, citation lookup, validate-bib.
- Hooks: session context, subagent context, pre-compact, context monitor, verify reminder, log reminder; fail-open and silent without `ploma.yaml`.
- Rules: eager core, style and limits; reference rules.
- Venue profiles (8) and discipline profiles (3).
- Templates for project files: CLAUDE.md section, rules, reports README, learnings, status line.

### Milestone 2: lifecycle

- Skills: brainstorm, lit-review, grill, spec, write, format, verify-claims, audit-reproducibility, proofread, review (peer, adversarial, seven-pass), devils-advocate, respond, checkpoint, compress-session, learn, deep-audit, commit. All 23 skills are installed.
- Agents: editor, domain and methods referees, domain reviewer, proofreader, verifier, claim-verifier (fresh-context Chain-of-Verification), code reviewer; each starts with the shared project context block.
- Scripts: consistency (numbers in the paper against pipeline results), style check, placeholders, sections, page map, arXiv rules, commit gate (prepare, override parsing).
- Commit gate: required `compile` and `bib`; recommended `consistency`, `claims`, `proofread`; `commit anyway: <reason>` on its own line, hard stop after three consecutive overridden commits.
- Analysis-pipeline project skill template.
- One eval case per skill under `evals/`.

### Field-test fixes

- Escaped DOIs and urls (`\_` and similar) are unescaped before lookup and duplicate checks.
- Unicode spaces (NBSP) are normalised in lookup titles and bib report evidence.
- Metric-key recommendation skips counts, ids, thresholds and hyperparameters, and reads one nesting level.
- Onboard proposes `document.discipline`, recommending `ml` only for ML venues.
- Doctor groups legacy-harness findings into one WARN per kind.
- The compile report keeps the raw build tail only on FAIL and lists LaTeX warnings as INFO.
