# Deep audit checks

The checks each deep-audit agent runs, with ids for the `Check:` field. Severities use the scale in
`${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/finding-format.md`. A check that cannot run (missing
input, tool error) is reported as not run, never as clean.

## Area 1: Config and project files

| Check | What | Severity |
|---|---|---|
| `config.doctor` | every doctor finding with status FAIL or WARN in the config, project-files, state and legacy-harness groups, one finding each (id, summary, observed, remediation) | FAIL: CRITICAL; WARN: MAJOR |
| `config.drift` | doctor `project-files.drift:*`: a generated rule differs from what `ploma.yaml` renders. Route `onboard`. | MAJOR |
| `config.receipt` | `receipt.py compare` rows hand_edited or missing. A hand-edited enforced file is MAJOR (onboard will overwrite it); a hand-edited created-once file is MINOR and usually intended | MAJOR or MINOR |
| `config.legacy` | doctor legacy-harness WARNs: vendored skills, hook entries or rules that duplicate ploma. Report the retirement checklist; never delete anything. | MAJOR |
| `config.gate` | `gate.py check`: a required check missing or STALE, a FAIL entry | MAJOR |
| `config.paths` | every path in `ploma.yaml` (document.main, document.root, build.bib_files, build.cwd, pipeline.run_from, pipeline.outputs_dir, literature.sources) exists | CRITICAL for document.main, else MAJOR |

## Area 2: Rules and CLAUDE.md

| Check | What | Severity |
|---|---|---|
| `rules.paths` | every repo path named in every `.claude/rules/*.md`, generated `ploma-*` rules and hand-written project rules alike (backticked paths, `paths:` frontmatter globs), and in the CLAUDE.md span between the ploma markers exists; a glob must match at least one file. Placeholders such as `<outputs.dir>` are resolved from the config first. | MAJOR |
| `rules.restated_fact` | a project rule that ploma did not generate (no generated-by line after its frontmatter), `.claude/rules/ploma-learnings.md` included, states a value `ploma.yaml` holds: the build engine, the bibliography tool, the venue or document class, the page budget, the main file. Quote the line; the fix deletes it or replaces it with "see ploma.yaml". Also the CLAUDE.md text outside the markers. | MAJOR |
| `rules.contradiction` | two rules, or a rule and `ploma.yaml`, disagree (a different engine, a different main file, a different outputs directory) | CRITICAL |
| `rules.commands` | every `/ploma:<name>` named in a project rule or CLAUDE.md is a skill the plugin ships (Glob `${CLAUDE_PLUGIN_ROOT}/skills/*/SKILL.md`) and every flag named appears in that skill's `argument-hint` | MINOR |
| `rules.markers` | exactly one ploma marker pair in CLAUDE.md, outside code fences | MAJOR |

The generated rules (with the generated-by line) restate config facts by design: that is not a finding. Drift between them and `ploma.yaml` is `config.drift`.

## Area 3: Outputs and reports

Scope: Markdown under `<outputs.dir>/`, excluding `session_logs/` (personal, gitignored) and `.cache/`.

| Check | What | Severity |
|---|---|---|
| `outputs.dangling` | a repo path a report cites (backticked path, `path:line`, Markdown link target, a `**File:**` header) no longer exists. Strip `:line` before checking. Paths inside fenced examples of a template are skipped. | MINOR, MAJOR when the report is the artifact of a gate entry |
| `outputs.dangling_line` | a cited `path:line` whose file exists but has fewer lines than cited | MINOR |
| `outputs.gate_artifacts` | every `artifact` in the gate file and the latest state events exists | MAJOR |
| `outputs.ledger_format` | every non-header line under `## Entries` in `learnings.md` matches the ledger pattern in `${CLAUDE_PLUGIN_ROOT}/skills/learn/references/ledger-format.md` | MINOR |
| `outputs.promoted_missing` | a ledger line marked `(promoted <date>)` whose rule line is absent from `.claude/rules/ploma-learnings.md` | MINOR |

Historical reports are records of what was true when written. A dangling path in an old dated
section is MINOR and the fix is a note ("file since removed"), never a rewrite of the finding.

## Area 4: Manuscript consistency

| Check | What | Severity |
|---|---|---|
| `manuscript.consistency` | each consistency finding (FAIL: CRITICAL, WARN: MAJOR, INFO: MINOR) with its manuscript location and the quoted number | as stated |
| `manuscript.spec` | when `<outputs.dir>/paper_spec.md` exists: a claim, section or page target in the spec that the manuscript contradicts | MAJOR |
| `manuscript.passport` | a passport claim whose manuscript location no longer holds the claimed number | MAJOR |
| `manuscript.labels` | a `\ref` or `\cref` to a label defined nowhere, a figure file included but absent | MAJOR |

Route `manuscript` always: report only, naming the skill (`/ploma:write`, `/ploma:proofread`,
`/ploma:audit-reproducibility`, `/ploma:compile`). Deep audit never edits `.tex` or `.bib`.

## Patterns past audits missed

- Docs promise a flag the skill does not have: grep the skill's `argument-hint` for every flag a rule or report tells the user to pass.
- An enumerating list (skills, rules, files) that no longer matches what is on disk although every count phrase was updated: count the list's rows against the directory.
- A summary paragraph patched phrase by phrase across rounds: when two findings hit the same paragraph, propose rewriting it.
- A statement that a component "runs" or "activates" when it is a pattern a skill follows, not a hook.
- A rule whose `paths:` scope names files that the rule's instructions never apply to, or a glob that matches nothing.

## Known false alarms

- Config facts inside the generated rules `ploma-manuscript.md` and `ploma-pipeline.md`: generated from `ploma.yaml` on purpose.
- Paths in session logs: personal history, out of scope.
- Paths and counts in dated sections of old reports and in the CHANGELOG under a released version: historical records.
- Placeholders such as `<outputs.dir>`, `<slug>`, `<YYYY-MM-DD>` in templates and reports: not paths.
- A hand-edited created-once file (README, ledger, state, learnings rule): those are meant to be edited.
