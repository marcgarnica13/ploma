# Changelog

## 0.2.0 (unreleased)

- Codex support: install from the same repo with `codex plugin marketplace add marcgarnica13/ploma` and `codex plugin add ploma@ploma`; skills are typed `$ploma:<name>`.
- Host detection; the session hook refreshes the `.ploma/plugin` link to the plugin root.
- Onboard writes per-host project files. On Codex: an `AGENTS.md` section with the rule bodies inlined, a `.codex/config.toml` export block, generated `.codex/agents/ploma-*.toml` agents, and `.agents/skills/` for the project skill.
- Switching hosts: run onboard on the new host; the old host's files are kept.
- Doctor `host` group: `host_mismatch`, `other_host_files`, `root_export_*`, `plugin_link`, `agents_md_size`.
- Hooks classify tool names instead of relying on matchers.
- Printed skill references are localized per host (`/ploma:<name>` or `$ploma:<name>`).
- Promoted learnings on Codex live in an `AGENTS.md` block.
- The `statusline` CLI action.
- A bootstrap line in every skill sets the plugin root when the shell lacks it.

## 0.1.0 (2026-10-29)

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
- Table cells are checked against their row's own entity, by name field, with method context from section rows; a wrong row, column or method gives a WARN that cites the repo-relative source.
- Each table's results source is voted table-wide per run directory; `%% ploma-source: <path>` pins it, with WARNs for missing or unused pins.
- Bibliography lookups FAIL as missing only for a dead DOI, or for an entry with no DOI that every source answered for and that carries no grey-literature markers; other absences are WARN "not found in Crossref or OpenAlex; confirm it exists".
- A passport claim goes stale only when its value is gone from the whole cited file.
- The format page map reads two-column PDFs by column.

### Known issues (0.1.1)

- Short row codes that differ from the results' entity names (e.g. "BERT-L" vs `bert_large`) are not checked across rows.
- `table_source_missing` prints an absolute path; the table density INFO counts the whole results pool rather than the voted source.
- `table_method_ambiguous` can fire on unrelated numeric tables; a section naming two methods takes the first.

