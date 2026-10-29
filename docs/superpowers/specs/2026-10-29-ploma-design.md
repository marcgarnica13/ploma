# ploma v0.1 design

**Date:** 2026-10-29
**Status:** APPROVED by Marc on the design forks (2026-10-29); reviewed by a builder check
**Scope:** Claude Code plugin `ploma`, a harness for LaTeX academic papers. Installed with `/plugin marketplace add marcgarnica13/ploma` and `/plugin install ploma@ploma`.
**Inputs:** `BRIEF.md`, `extraction/research/01-05`, the verbatim traces harness under `extraction/`, Marc's answers to the three design forks (2026-10-29).

---

## 1. Intent

Marc writes LaTeX papers in several repos. Each repo today carries a hand-adapted copy of the same `.claude/` harness, with project facts (manuscript path, build command, venue, pipeline gotchas) restated in about ten files. Every change to the stack forces edits across those files, and the copy drifts. Six of the twenty skills were never run because nothing recommended them, and the costliest real pain (numbers disagreeing between figures, tables and text; the page budget managed by hand; referee responses stalled at scaffold) was never caught by the harness.

ploma turns that harness into one installable plugin. A paper repo declares its facts once in `ploma.yaml`. Skills, agents, hooks and rules read the config instead of restating it. An onboarding skill detects the facts by reading the repo, proposes the config, and writes project files only after approval. A doctor says whether the repo is ready. A lifecycle of stages, each owned by one skill, is recommended from state that survives sessions.

The reference model for "harness" is lisa (intent captured up front, state of the art consulted, self-verification with evidence, state files, a doctor, bounded loops that escalate) and Marc's own tramat plugin (manifest plus schema, deterministic scripts, doctor, `UPSTREAMS.md`).

## 2. Goals, non-goals, anti-goals

**Goals**

1. Install into any LaTeX paper repo in two commands, on both of Marc's hosts (one has SSH to GitHub hanging, so HTTPS must work).
2. `/ploma:onboard` proposes a correct `ploma.yaml` for the traces paper with zero wrong detections and writes nothing before approval.
3. All twenty skills of the traces harness are ported, paper-agnostic, parameterized by `ploma.yaml` (Marc's decision 2026-10-29).
4. The three real pain points get a deterministic answer: a text-vs-table-vs-results consistency pass, a page budget report with a cut plan, and a response-to-referees that ingests any report format and finishes the document.
5. Enforcement is advisory plus one gate: `/ploma:commit` refuses to commit until a fresh verdict file shows the required checks passed, with a bounded, logged override (Marc's decision).
6. Learnings live in a single committed ledger with human-gated promotion into a project rule (Marc's decision).
7. Everything deterministic is a script with tests; everything judgmental is a skill or agent that quotes the script output as its audit record.

**Non-goals (v0.1)**

- Proposals and theses. `document.type` is reserved and validated, and any non-paper type yields a clear "not supported in v0.1" message.
- Reimplementing superpowers. ploma sequences `superpowers:brainstorming`, `superpowers:writing-plans` and `superpowers:verification-before-completion`; it does not copy them.
- Vendoring text from academic-research-skills (CC-BY-NC-4.0). Ideas only.
- A Stop hook that blocks session end. Rejected by Marc for v0.1.
- Cross-runtime variants (Codex, Cursor). Claude Code only.

**Anti-goals (what would make this a failure even if it works)**

- Soccer, process-mining, Springer, LLNCS or Python-pipeline text left in any agent or skill body. All of it moves to `ploma.yaml`, venue profiles or discipline cards.
- A critic that edits the manuscript. Report-only is a rule, not a preference.
- A check that reports clean without having run. Pasted tool output is the audit record.
- A skill that asks Marc something the repo or config already answers.
- Sentence-level em-dashes in any prose ploma writes into a manuscript. A co-author rejected a plan over them.

## 3. Constraints

From the official plugin docs (verified 2026-10-29, see `extraction/research/05`):

- Plugins cannot ship `.claude/rules/` or a `CLAUDE.md`. Always-on guidance goes through a `SessionStart` hook's `hookSpecificOutput.additionalContext` (10,000 character cap per string) or files that onboard writes into the project.
- `context: fork` is a skill frontmatter field, not a Task parameter. The traces harness misuses it in six skills; ploma does not.
- Plugin agents ignore `permissionMode`, `hooks` and `mcpServers`. Hooks ship in `hooks/hooks.json`.
- Scripts go in `scripts/`, not `bin/`. Component paths start with `./`.
- The marketplace entry name must equal the manifest name. Install string: `/plugin install ploma@ploma`.
- `claude plugin validate .` must pass. The build on r2d2 (Claude Code 2.1.312) has no `--strict` flag; it offers `--profile <name>` for catalog-submission checks. The brief's `--strict` is read as "validate with no warnings".
- `SubagentStart` hooks can return `hookSpecificOutput.additionalContext`; lisa's `inject-rules.sh` relies on it in production. Fallback if it ever fails: the calling skill passes the config summary in the agent prompt.
- `userConfig` values reach hooks as `CLAUDE_PLUGIN_OPTION_<KEY>` and skills as `${user_config.KEY}`; skills pass them to scripts as arguments (`cite_lookup.py --mailto ...`).
- Private repo install uses the user's own git credentials. Document `gh auth setup-git` and `CLAUDE_CODE_PLUGIN_PREFER_HTTPS=1`.

From the environments:

- r2d2 (this session) has no TeX toolchain. Compile and format are structure-tested here with stored log fixtures; `traces-16` runs them on real TeX.
- Python 3 is the only runtime dependency for hooks and scripts. PyYAML is optional (see §6.1).
- Marc's working style (BRIEF §2): options at every fork with a recommended one first; short direct sentences; no em-dashes; check disk before regenerating; edit only the sections being worked on; raise contradictions as open flags, never silently change prose; compact horizontal figures.

## 4. Repository layout

Single plugin at the repo root, tramat style. Marketplace `source: "./"`.

```
ploma/
  .claude-plugin/
    plugin.json                 # name ploma, version 0.1.0, userConfig for mailto/API keys
    marketplace.json            # name ploma, one plugin, source "./"
  skills/<name>/SKILL.md        # 23 skills, each < 500 lines, references/ and scripts/ as needed
  agents/<name>.md              # 8 agents
  hooks/hooks.json              # SessionStart, SubagentStart, PreCompact, PostToolUse, Stop
  hooks/*.py                    # fail-open python3, state under <project>/.ploma/
  scripts/*.py                  # deterministic checks (stdlib + optional PyYAML), --json output
  rules/eager/*.md              # injected at SessionStart and SubagentStart (budgeted < 7,000 chars)
  rules/reference/*.md          # loaded on demand by skills that cite them
  venues/*.yaml                 # venue profiles (page budget, cite style, referee pools, peeves)
  disciplines/*.yaml            # discipline cards (paper types, reproducibility norms)
  templates/                    # project files onboard composes from (CLAUDE.md section, rules, README)
  templates/project-skills/     # skills onboard can copy into a project (analysis-pipeline)
  schemas/*.schema.json         # ploma.yaml, venue profile, verdict, passport, state
  examples/sample-paper/        # tiny compilable article-class paper used by tests and evals
  evals/<case>/                 # claude plugin eval cases, at least one per skill
  tests/                        # pytest for scripts and hooks, run on r2d2
  docs/superpowers/{specs,plans}/
  README.md  UPSTREAMS.md  CHANGELOG.md  LICENSE
```

## 5. Project config: `ploma.yaml`

Written by `/ploma:onboard` at the repo root. Validated against `schemas/ploma.schema.json`. Every fact that is hard-coded in the traces harness maps to a key here.

```yaml
ploma: "0.1"
document:
  type: paper                        # paper | proposal | thesis; only paper in v0.1
  main: manuscript/samplepaper.tex   # resolved by \documentclass search
  root: manuscript
  title: "Capturing Team Strategy in European Football via Process Mining"
  slug: samplepaper                  # used in report filenames
  anonymized: true
  discipline: ml                     # key into disciplines/*.yaml
build:
  command: "make"                    # honoured verbatim, run from build.cwd; null = latexmk fallback
  cwd: manuscript
  engine: pdflatex                   # pdflatex | xelatex | lualatex
  bib_tool: bibtex                   # bibtex | biber
  bib_files: [manuscript/mybib.bib]
  pdf: manuscript/samplepaper.pdf
  log: manuscript/samplepaper.log
  overfull_threshold_pt: 10
venue:
  profile: springer-ml               # key into venues/*.yaml or ploma.d/venues/*.yaml
  doc_class: llncs                   # detected
  page_budget: 13                    # null if unknown
  page_budget_includes_refs: false
  cite_style: numeric                # numeric | author-year
reviews:
  glob: "review/*.md"                # prior-round referee reports, any text format
outputs:
  dir: quality_reports
style:
  sentences: short-direct
  forbid_em_dash: true
  forbid_phrases: []                 # appended to the shipped slop list
  figures: compact-horizontal
pipeline:                            # optional; absent or enabled:false disables the code add-on
  enabled: true
  language: python
  run_from: src
  rerun: "uv run python notebooks/discovery/parse_statsbomb_matches.py"
  outputs_dir: src/results
  metric_keys: [avg_fitness, generalization, dependency]
  env_contract: [MONGO_USER, MONGO_PWD, MONGO_STR, TAGS_FILE, RESULTS_FILE, STATSBOMB_DATA_DIR]
  gotchas:
    - "TAGS_FILE is read at import time in parsers/soccerlogs.py"
    - "Activity key format action##zone must be preserved"
    - "Pitch coordinates are flipped (y -> FIELD_WIDTH - y); verify orientation"
  tolerances: {counts: exact, metrics: 0.01, aggregates: 0.02, percentages_pp: 0.1}
limits:                              # overrides of rules/eager/limits.md defaults
  review_rounds: 5
  cove_regenerations: 2
  doi_lookups_per_run: 50
dependencies:
  superpowers: soft
```

Resolution rules:

- Paths are relative to the repo root.
- `ploma.d/` next to `ploma.yaml` holds committed project-local overrides: `ploma.d/venues/<key>.yaml` and `ploma.d/disciplines/<key>.yaml` shadow the shipped files of the same key.
- There is no local override file in v0.1. Machine-specific values (API keys, mailto) live in plugin `userConfig`, not in the repo.
- `scripts/ploma_config.py` is the single loader. Skills call it (`--json`) rather than parsing YAML themselves. Agents receive the resolved summary through the SubagentStart hook.

## 6. State and files on disk

### 6.1 Where things live

| Path | Committed | Owner | Content |
|---|---|---|---|
| `ploma.yaml` | yes | onboard, hand edits | project config |
| `ploma.d/` | yes | user | venue and discipline overrides |
| `<outputs.dir>/` (default `quality_reports/`) | yes | skills | every report, plan, spec, passport, verdict, learnings |
| `<outputs.dir>/ploma-state.yaml` | yes | `scripts/state.py` | lifecycle state (§6.2) |
| `<outputs.dir>/verdicts/commit-gate.json` | yes | compile, validate-bib, consistency, verify-claims, proofread | the commit gate verdict (§6.3) |
| `<outputs.dir>/learnings.md` | yes | `/ploma:learn` | single learnings ledger |
| `<outputs.dir>/session_logs/` | no (gitignored) | skills, hooks | session logs |
| `<outputs.dir>/.cache/` | no | scripts | per-project caches |
| `<outputs.dir>/ploma-receipt.json` | yes | onboard | apply receipt: files written, sha256, ownership mode |
| `.ploma/` | no | hooks | transient hook state (context monitor, pre-compact, reminders) |
| `.claude/rules/ploma-*.md` | yes | onboard (enforced mode) | path-scoped rules generated from `ploma.yaml` |
| `CLAUDE.md` marker section | yes | onboard (merged mode) | short pointer block between `<!-- ploma:begin -->` and `<!-- ploma:end -->` |
| `${CLAUDE_PLUGIN_DATA}/cache/` | n/a | `cite_lookup.py` | cross-project citation API cache |

Decision on session logs: gitignored by default, matching the traces repo. Committed checkpoints (`/ploma:checkpoint`) are the durable record. Rationale: logs are verbose and personal; checkpoints are curated.

PyYAML: scripts `import yaml` when available. When it is not, they fall back to `scripts/_yamlmini.py`, a tested loader for the subset `ploma.yaml` and the shipped profiles use (nested maps, lists, scalars, comments; no anchors, no multi-line strings). The doctor reports which loader is active. Rationale: the plugin must work in a fresh TeX-only environment without a pip install.

### 6.2 Lifecycle state

`<outputs.dir>/ploma-state.yaml` is an append-friendly record that `scripts/state.py` reads and writes. Skills never hand-edit it.

```yaml
ploma_state: "0.1"
stage: write                    # last stage a skill ran
rounds: {review: 1, respond: 0}
events:
  - {at: 2026-10-29T10:12:00Z, skill: compile, status: PASS, artifact: quality_reports/compile_samplepaper.md, pages: 14}
  - {at: 2026-10-29T10:40:00Z, skill: validate-bib, status: PASS, artifact: quality_reports/bib_audit_semantic.md}
```

`scripts/state.py next` returns the recommended next stage from the lifecycle order (§7) and the last status per stage. The SessionStart hook and `/ploma:status` render it. Rule: a recorded status is a claim about the past; `/ploma:status` re-checks freshness against manuscript hashes before recommending (lisa `stale-state-claims`).

### 6.3 Commit gate verdict

`<outputs.dir>/verdicts/commit-gate.json`, schema `schemas/verdict.schema.json`:

```json
{
  "schema": 1,
  "manuscript_sha": "<sha256 over all .tex and .bib under document.root>",
  "checks": {
    "compile":     {"status": "PASS", "at": "...", "artifact": "...", "pages": 14, "overfull": 0, "undefined": 0},
    "bib":         {"status": "PASS", "at": "...", "artifact": "..."},
    "consistency": {"status": "PASS", "at": "...", "artifact": "..."},
    "claims":      {"status": "PASS", "at": "...", "artifact": "..."},
    "proofread":   {"status": "WARN", "at": "...", "artifact": "...", "open_high": 2}
  },
  "overrides": [{"at": "...", "reason": "camera-ready deadline", "checks": ["proofread"]}]
}
```

Each producing skill updates its own entry through `scripts/gate.py record`. `scripts/gate.py check` reports: FRESH or STALE (sha mismatch) per check, required checks missing, and the verdict. Required for commit: `compile`, `bib`, `consistency`. Recommended: `claims`, `proofread` (WARN when missing or stale). Any FAIL in a required check halts `/ploma:commit`.

Who produces each entry: `compile` by `/ploma:compile`; `bib` by `/ploma:validate-bib`; `consistency` by `scripts/consistency.py`, which `/ploma:commit` runs itself when the entry is missing or stale (it is deterministic and needs no pipeline; with `pipeline.enabled` it also checks results files); `claims` by `/ploma:verify-claims`; `proofread` by `/ploma:proofread`. The passport under `<outputs.dir>/passports/` is populated and updated by `/ploma:audit-reproducibility` (BRIEF §8) and read by the consistency pass; it is never required for the gate.

Override (Marc's decision 2026-10-29): a required FAIL can be overridden by writing `commit anyway: <reason>`. The reason is recorded in the commit body and in `overrides[]`. After three consecutive overridden commits, `/ploma:commit` refuses until at least one required check passes again; the doctor warns from the second consecutive override. Recommended checks never block.

There is no 0-100 quality score. The traces harness scored commits against 80/90/95 thresholds with a script that never existed; ploma's gate is per-check PASS, WARN, FAIL. The `limits` block carries loop caps and tolerances only.

## 7. Lifecycle and skills

Stages in order. Each stage has one owning skill. `/ploma:help` and the session status line recommend the next stage from state.

| # | Stage | Skill | Reads | Writes | Loops and caps |
|---|---|---|---|---|---|
| 0 | Install | `/ploma:onboard` | repo (read-only inventory) | `ploma.yaml`, project files (§8) | re-run is an absorption run |
| 0b | Health | `/ploma:doctor` | config, repo, toolchain | report in chat; `--json` | none, read-only |
| 1 | Brainstorm | `/ploma:brainstorm` | topic, `master docs` if any | `research_ideation_<topic>.md` | CoVe, 2 regenerations |
| 1b | Literature | `/ploma:lit-review` | topic, existing `.bib` | `lit_review_<topic>.md` + verified BibTeX | CoVe, 2 regenerations |
| 2 | Grill | `/ploma:grill` | spec or idea | `decisions/<date>_<topic>.md` | one question at a time; stops when no open decision remains |
| 3 | Spec | `/ploma:spec` | grill decisions | `paper_spec.md` (binding contract) | CoVe on cited papers |
| 4 | Write | `/ploma:write <section>` | spec, manuscript | `<section>_suggestion.tex` sibling + diff | self-check: style, consistency; never edits the manuscript |
| 5 | Compile | `/ploma:compile` | build config | PDF, `compile_<slug>.md`, gate entry | fix first error, max 2 rebuilds |
| 5b | Format | `/ploma:format` | PDF, venue profile | `page_budget_<slug>.md`, `presubmit_<slug>.md` | none |
| 6 | Validate | `/ploma:validate-bib`, `/ploma:verify-claims`, `/ploma:audit-reproducibility`, `/ploma:proofread` | manuscript, bib, results | reports, gate entries, passport | DOI lookups capped (50 per run) |
| 7 | Review | `/ploma:review [--adversarial|--peer <venue>|--seven-pass]`, `/ploma:devils-advocate` | manuscript, venue profile | `peer_review_<slug>/`, `paper_review_<slug>_round<N>.md` | adversarial 5 rounds; R&R capped at r3; variance N ≤ 5 |
| 8 | Respond | `/ploma:respond <report>` | referee reports, revised manuscript | `response_to_referees.md`, coverage matrix | CoVe on location claims, 2 regenerations |
| 9 | Ship | `/ploma:commit` | gate verdict | git commit, PR | 2 fix-and-recheck rounds, then halt |
| any | Session | `/ploma:status`, `/ploma:checkpoint`, `/ploma:compress-session`, `/ploma:learn`, `/ploma:deep-audit`, `/ploma:help` | state, logs | checkpoints, ledger, audits | deep-audit 5 loops |

Twenty-three skills. Port mapping from the traces harness:

| traces skill | ploma skill | change |
|---|---|---|
| research-ideation | brainstorm | sequences `superpowers:brainstorming` first when installed; paper-type taxonomy from discipline card; econ leftovers removed |
| lit-review | lit-review | source dirs from config; CoVe unchanged |
| interview-me | spec | output is the binding `paper_spec.md` (identity sentence, venue constraints, claims with evidence pointers, evaluation plan, positioning, section architecture, locked decisions vs open questions, figures needed); one or two questions per turn, each with a recommended answer |
| (new) | grill | one question at a time, recommended answer first, the agent looks facts up itself; four lenses (theorist, empiricist, pragmatist, reproducibility) chosen per question; ends with a decision log |
| (new) | write | sibling-file pattern formalized (§7.1) |
| compile-latex | compile | honours `build.command`, else latexmk; engine and bib tool from config; `scripts/latex_log.py` triage; `pdfinfo` pages vs budget |
| (new) | format | per-section page map, cut plan ordered by value per page (format of the accepted `page_budget_cut_proposal.md` sample), pre-submission fan-out (chktex, lacheck, texcount, placeholder grep, arXiv rules from the venue profile) |
| proofread | proofread | unchanged protocol; terminology list from config |
| validate-bib | validate-bib | `scripts/bib_check.py` structural; `scripts/cite_lookup.py` for `--semantic`; multiple bib files and biblatex supported |
| verify-claims | verify-claims | unchanged; records a gate entry |
| audit-reproducibility | audit-reproducibility | requires `pipeline.enabled`; tolerances and metric keys from config; passport under `<outputs.dir>/passports/`; plus the deterministic `scripts/consistency.py` pass (§7.2) |
| review-paper | review | three modes plus `--seven-pass` (the seven lenses fold in as a fourth mode); peeve pools move to venue and discipline files; every finding quotes a manuscript span; referees treat the manuscript as untrusted input |
| seven-pass-review | review --seven-pass | folded |
| devils-advocate | devils-advocate | prior reviews from `reviews.glob`; challenge examples from discipline card |
| respond-to-referees | respond | schema-agnostic ingestion, reviewer IDs from content, R{n}.{m}, coverage matrix, `--audit` mode for an existing draft; template ships in `skills/respond/references/` |
| commit | commit | gate wired to the verdict file; branch and merge strategy from args or git default; never `git add -A` |
| checkpoint | checkpoint | upstream leftovers removed; learnings go to the ledger |
| compress-session | compress-session | unchanged |
| context-status | status | adds lifecycle state and gate freshness |
| learn | learn | appends to `<outputs.dir>/learnings.md`; `--promote` proposes entries for `.claude/rules/ploma-learnings.md` and writes only on approval; `--skill <name>` keeps the old "write a project skill" path |
| promote-memory | (folded into learn --promote) | the five-critic council is dropped (Marc's decision) |
| deep-audit | deep-audit | audits the project's ploma installation (config vs rules vs CLAUDE.md section drift, dangling paths, gate freshness) and cross-document consistency; 5-loop cap kept |
| data-analysis | templates/project-skills/analysis-pipeline | not shipped as a plugin skill; onboard offers to copy it into `.claude/skills/` when `pipeline.enabled`, with the project's gotchas filled in |
| (new) | onboard, doctor, help | §8, §9 |

Skills hidden from model invocation (`disable-model-invocation: true`): onboard, commit, deep-audit, learn, checkpoint, compress-session.

### 7.1 The write skill

`/ploma:write <section-label-or-file> [--from-spec] [--merge]`

1. Reads `paper_spec.md` (if present), the target section, and the style block.
2. Drafts to a sibling file `<root>/<section>_suggestion.tex` with a header comment naming the source section, the spec items it serves, and the date. It never edits the manuscript.
3. Runs a self-check before showing anything: style (sentence length, em-dash, slop phrases via `scripts/style_check.py`), notation consistency with the rest of the manuscript, numbers present in the draft must exist in the manuscript or results (via `scripts/consistency.py`). Findings are listed with location, current text, fix and severity.
4. Shows a diff against the current section and the open flags (contradictions found, not fixed).
5. `--merge` applies the sibling file over the section only after approval, then recommends `/ploma:compile`.
6. Figures: every `\includegraphics` the draft introduces gets a `% ploma:source <script> <args>` comment when `pipeline.enabled`; the doctor warns on figures without one.

### 7.2 The consistency pass

`scripts/consistency.py <main.tex> [--results <dir>] [--passport <yaml>]` is deterministic:

- Extracts numbers with units or percent signs from the abstract and introduction and checks each appears in the body, a table, or a results file within the configured tolerance.
- Extracts table cells and checks them against `metric_keys` in results files when `pipeline.enabled`.
- Checks every passport claim's status.
- Output: a findings list (rule id, location, number, where it was looked for, verdict). Exit 1 on any FAIL.

`/ploma:audit-reproducibility` runs it first, then the judgmental matching for claims the script could not place. `/ploma:commit` requires its gate entry.

## 8. Onboard

`/ploma:onboard [--dry-run] [--yes]`, hidden from model invocation.

1. **Refuse or route.** If `ploma.yaml` exists, this is an absorption run: re-inventory, show what changed, absorb answered gaps, never clobber hand edits. If the repo has no `.tex` file, stop with the message that ploma v0.1 supports LaTeX papers only.
1b. **Legacy harness detection** (Marc's decision 2026-10-29: detect and report, do not retire). The inventory flags a legacy vendored harness when it finds `.claude/skills/<name>` whose name matches a ploma skill or its traces predecessor, hook entries in `.claude/settings.json` pointing at `.claude/hooks/`, a `.claude/statusline` or `scripts/statusline.sh`, or `.claude/rules/*.md` that restate build or venue facts. Onboard lists each conflict with its consequence (double-firing hooks, duplicate skill names, rules contradicting `ploma.yaml`) as a retirement checklist, and withholds its `.claude/settings.json` suggestions while legacy hook entries remain. It deletes and moves nothing. The doctor repeats the checklist as WARN until it is clear.
2. **Inventory, read-only.** `scripts/inventory.py --json` detects: main file (the `.tex` containing `\documentclass`, preferring the one with `\begin{document}`; several candidates become a question), `\input`/`\include` tree, document class and options, engine hints (`fontspec` means xelatex or lualatex), bib tool (`biblatex` with `\addbibresource` means biber; `\bibliographystyle` means bibtex), bib files, Makefile targets or `latexmkrc`, figures and whether they carry provenance comments, candidate reviews directory, candidate results directory and language of a sibling code tree, git remote, title, anonymity (author block commented or `\anonymous`), page count of an existing PDF, enabled superpowers plugin on either marketplace name.
3. **Venue guess.** Map document class to a shipped profile (`llncs` to `springer-ml` or `llncs-conference`, `IEEEtran` to `ieee`, `acmart` to `acm`, `elsarticle` to `elsevier`, `article` to `generic`). The guess is a question with a recommended answer.
4. **Gaps.** Only questions the repo cannot answer by reading harder: venue profile when ambiguous, page budget, whether the sibling code tree is the paper's pipeline, metric keys and gotchas when it is. Each question carries a recommended answer. Everything else is derived.
5. **Propose.** Show the full `ploma.yaml` and the list of files it will write, with ownership modes:
   - enforced (regenerated from config on every run, diff shown): `.claude/rules/ploma-manuscript.md`, `.claude/rules/ploma-pipeline.md`
   - created-once (never overwritten): `quality_reports/README.md`, `quality_reports/learnings.md`, `quality_reports/ploma-state.yaml`, optional `.claude/skills/analysis-pipeline/SKILL.md`
   - merged (marker-delimited): the `CLAUDE.md` section, `.gitignore` entries
   - proposed, not written: `.claude/settings.json` additions (`plansDirectory`, Bash allow-list for the build command, `pdftotext`, `pdfinfo`, `chktex`); plugins cannot grant permissions, so this stays a suggestion the user applies.
6. **Write after approval** and record `quality_reports/ploma-receipt.json`.
7. **Verify.** Run `scripts/doctor.py --json` and report. Onboard must end READY or say exactly why not.

## 9. Doctor

`/ploma:doctor [--json] [path]`, read-only, never asks "proceed?". `scripts/doctor.py` renders grouped checks, each PASS, WARN, FAIL, INFO or SKIP with a reason, and one verdict: READY (no FAIL, no WARN), READY_WITH_WARNINGS, NOT_READY. INFO and SKIP never affect the verdict. Observed facts and remediation are separate lines.

Severity assignment that matters for AC3: optional linters (`chktex`, `lacheck`, `texcount`) absent is SKIP with a reason; figures without a provenance comment is INFO unless `pipeline.figure_provenance: required`; a PDF older than its sources is WARN, cleared by `/ploma:compile`. So a freshly onboarded and compiled traces repo reaches READY.

Groups:

1. Runtime: python3, YAML loader in use, git.
2. Config: `ploma.yaml` present, schema-valid, every path exists, `document.type` is `paper`, venue profile resolves, discipline card resolves.
3. Toolchain: engine binary, bib tool, `pdfinfo`, `pdftotext` (WARN when absent), `chktex`, `lacheck`, `texcount` (SKIP when absent). Build command runs `--dry-run` where possible (`make -n`).
4. Manuscript: a PDF exists and is newer than the sources (WARN if stale), bib keys resolve (structural check), figures have provenance comments when `pipeline.enabled` (INFO, or WARN when `pipeline.figure_provenance: required`).
5. Project files: the enforced rules match what config would generate (drift is a WARN with the diff summary), the `CLAUDE.md` section is present, `.gitignore` covers `.ploma/` and session logs, receipt present.
6. State: gate verdict freshness, stage recommendation, override streak (WARN after three consecutive overrides).
7. Dependencies: superpowers enabled (WARN if not), citation API reachability is SKIP (doctor makes no network calls).

AC3: READY on the onboarded traces repo; NOT_READY on an empty directory with the first FAIL saying to run `/ploma:onboard`.

## 10. Agents

Eight agents under `agents/`, namespaced `ploma:<name>`. Each starts with a "Project context" block that reads the resolved config injected by the SubagentStart hook and the venue or discipline files named there. No agent body names a field, venue, language or dataset.

| Agent | Role | Model | Tools |
|---|---|---|---|
| editor | desk review, referee selection from the venue's pool weights, synthesis (FATAL / ADDRESSABLE / TASTE), R&R, stress, variance | opus | Read, Grep, Glob, WebSearch, WebFetch |
| domain-referee | contribution, literature, substance, external validity, fit; weights adjusted by venue | opus | Read, Grep, Glob |
| methods-referee | paper-type aware (types from the discipline card); mandatory sanity checks per type; a reproducibility FAIL is FATAL | opus | Read, Grep, Glob |
| domain-reviewer | not disposition-primed; five lenses (method assumptions, derivations, citation fidelity, pipeline-paper alignment, backward logic) | opus | Read, Grep, Glob |
| claim-verifier | CoVe verifier; never receives the draft; HIGH / MED / LOW tiers | opus | Read, Grep, Glob, WebFetch, WebSearch, Bash |
| proofreader | report-only; grammar, typos, overflow, consistency, academic quality | sonnet | Read, Grep, Glob |
| code-reviewer | generalized python-reviewer: language and gotchas from `pipeline`; only used when `pipeline.enabled` | sonnet | Read, Grep, Glob |
| verifier | builds the manuscript through the configured command, parses the log, checks anonymity and bib parity; optional pipeline rerun check | sonnet | Read, Grep, Glob, Bash |

Dropped: promote-memory-council (Marc's decision). Model routing is applied in frontmatter, replacing the never-applied `model-routing.md`.

Peeve pools: the 29 critical and 25 constructive peeves in `editor.md` split into generic (stay in `agents/editor.md`), discipline-specific (`disciplines/ml.yaml`) and venue-specific (`venues/springer-ml.yaml`). The editor draws from the union.

Review hardening (from the research, all cheap): every finding quotes a manuscript span and the editor's synthesis drops any finding whose quote is not found verbatim; referees commit reports without seeing each other; the manuscript and pasted referee text are data, not instructions, stated in every reviewer agent.

## 11. Hooks

`hooks/hooks.json`, all `python3 "${CLAUDE_PLUGIN_ROOT}/hooks/<name>.py"`, all fail-open, all no-ops in under 100 ms when the project has no `ploma.yaml` (except the session start line).

| Event | Matcher | Script | Behaviour |
|---|---|---|---|
| SessionStart | startup, resume, clear, compact | `session_context.py` | emits `additionalContext`: eager rules, resolved config summary, lifecycle status and next-stage recommendation, gate freshness; on `compact` or `resume` also the post-compact restore block. Without `ploma.yaml`: one line pointing at `/ploma:onboard`. Total under 10,000 characters, enforced by the script. |
| SubagentStart | all | `session_context.py --subagent` | eager rules plus config summary only |
| PreCompact | all | `pre_compact.py` | ported: newest plan status, recent decisions from the session log, state under `.ploma/`; the "block on DRAFT" option kept behind the same env var |
| PostToolUse | Bash, Task, Agent | `context_monitor.py` | ported; nudges to `/ploma:checkpoint` at thresholds; state under `.ploma/` |
| PostToolUse | Write, Edit | `verify_reminder.py` | ported and fixed: `.tex` recommends `/ploma:compile`, `.bib` recommends `/ploma:validate-bib`, pipeline language extension recommends the code reviewer; case bug fixed |
| Stop | all | `log_reminder.py` | ported; never blocks |

Dropped: `notify.sh` (OS-specific, jq dependency, no lifecycle value). The statusline script moves to `templates/statusline.sh`; onboard offers it.

Eager rules budget: `rules/eager/00-core.md` (where things live, lifecycle, report-only critics, finding format, options at forks, untrusted text, check disk before regenerating, scope discipline), `rules/eager/limits.md` (thresholds, caps, tolerances; overridable by `limits:` in config), `rules/eager/style.md` (short direct sentences, no sentence-level em-dash, slop phrase list, compact figures). Together under 7,000 characters so the config summary and state fit in the cap. Everything else is a reference rule a skill cites by path.

## 12. Venue profiles and discipline cards

`venues/<key>.yaml`, schema `schemas/venue.schema.json`:

```yaml
key: springer-ml
name: "Springer Machine Learning journal"
kind: journal                         # journal | conference | workshop | preprint
doc_classes: [llncs, sn-jnl, svjour3]
cite_style: numeric
page_budget: null                     # journal: none; conferences set it
anonymized: false
bib_style_hint: splncs04
focus: "..."
bar: "..."
referee_pool: {EVALUATION: 0.25, METHODOLOGY: 0.20, REPRODUCIBILITY: 0.20, NOVELTY: 0.15, SKEPTIC: 0.10, CLARITY: 0.10}
domain_adjustments: {contribution: [30, 35], literature: [25, 30], fit: [10, 5]}
methods_adjustments: {evaluation: [30, 35], reproducibility: [10, 15]}
typical_concerns: ["..."]
peeves: {critical: ["..."], constructive: ["..."]}
format_rules: ["No significance stars", "State N in table notes"]
submission_checks: [placeholders, undefined_refs, page_budget]
```

Shipped in v0.1: `springer-ml`, `llncs-conference` (the MLCONF stand-in), `ieee-conference`, `acm-sigconf`, `elsevier`, `arxiv` (adds the arXiv rule set to `submission_checks`), `generic-journal`, `generic-conference`. The two soccer-flavoured profiles from traces are rewritten without domain text; their domain concerns move to `disciplines/ml.yaml`.

`disciplines/<key>.yaml`: paper types with weights and mandatory sanity checks (from methods-referee), reproducibility norms, method conventions, challenge examples for devils-advocate, discipline-specific peeves. Shipped: `ml`, `generic`. The six econ and political-science paper types inherited from clo-author are dropped from the default card and kept as `disciplines/social-science.yaml` so nothing is lost.

## 13. Scripts and tests

All under `scripts/`, python3 stdlib, optional PyYAML, `--json` output, exit codes documented, each with pytest coverage under `tests/` using `examples/sample-paper/` and stored fixtures (logs, bib files, referee reports). Each check is falsified in its tests: the test suite contains a known-bad input per check and asserts the check fails on it (lisa `falsifiable-checks`).

| Script | Purpose |
|---|---|
| `ploma_config.py` | load, validate, resolve `ploma.yaml`; `--json` |
| `_yamlmini.py` | fallback YAML subset loader |
| `inventory.py` | read-only repo detection for onboard |
| `doctor.py` | grouped readiness checks |
| `state.py` | read and append lifecycle state; `next` |
| `gate.py` | record and check the commit gate verdict |
| `latex_log.py` | log triage: errors with file and line, undefined refs and cites, overfull above threshold, rerun needed |
| `pdf_pages.py` | page count and per-section page map (`pdfinfo`, `pdftotext -layout` heading grep) |
| `bib_check.py` | cite keys vs entries across bib files, biblatex resources, near-miss keys, duplicates by DOI and normalized title |
| `cite_lookup.py` | existence check Crossref then OpenAlex then Semantic Scholar, cached under `${CLAUDE_PLUGIN_DATA}`; `mailto` and keys from `userConfig` |
| `consistency.py` | §7.2 |
| `style_check.py` | sentence length, em-dash, slop phrases, on a `.tex` or a sibling draft |
| `placeholders.py` | TODO, XXX, `\todo`, `??`, example.com, `\today` |
| `receipt.py` | write and compare the onboard apply receipt |

Not scripted in v0.1 (judgment-heavy, stays in skills): referee report decomposition, claim extraction for CoVe, cut-plan drafting, review synthesis.

Tests run on r2d2 with `python3 -m pytest tests/`. Compile-dependent paths are covered by fixtures, and `traces-16` runs the real thing.

## 14. Evals, validation, CI

- `evals/<skill>/prompt.md` plus graders for every skill: `tool_used: Skill` with the skill name, a `file_exists` grader for the report path where applicable, and an `llm` rubric from the skill's output contract. Cases run against `examples/sample-paper/`.
- `claude plugin validate .` locally before every release; a GitHub Actions workflow runs pytest and a Python manifest validator (`tests/test_manifest.py`) on every push, since the Claude CLI is not assumed in CI.
- Release: bump `version` in `plugin.json`, add a `CHANGELOG.md` entry, tag `ploma--v<version>`.

## 15. Install documentation

README documents both hosts:

```
gh auth login && gh auth setup-git          # HTTPS credentials
export CLAUDE_CODE_PLUGIN_PREFER_HTTPS=1    # skip the SSH probe (needed on Marc's paper host)
/plugin marketplace add marcgarnica13/ploma
/plugin install ploma@ploma
/ploma:onboard
```

Updates: `/plugin marketplace update ploma`, then `/reload-plugins`.

## 16. Acceptance criteria (from BRIEF §9, kept verbatim in intent)

1. `claude plugin validate .` passes with no warnings; install works on both hosts.
2. `/ploma:onboard` on traces proposes a correct `ploma.yaml` with zero wrong detections and writes only after approval.
3. `/ploma:doctor` is READY on traces after onboarding and NOT_READY with actionable findings on an empty repo.
4. `/ploma:compile` reproduces today's `make` result and reports overfull boxes, undefined references and page count vs budget (run by `traces-16`).
5. `/ploma:validate-bib --semantic` and `/ploma:verify-claims` reproduce the two existing PASS reports.
6. `/ploma:review --peer springer-ml` produces desk review, two referee reports and an editorial decision in the same structure as today, with no soccer-specific text in agent bodies.
7. `/ploma:respond extraction/samples/review/review1.md` yields a numbered concern list with reviewer IDs read from content.
8. `/ploma:grill` runs one question at a time with recommended answers and ends with a written decision log.
9. `evals/` has at least one case per skill; `UPSTREAMS.md`, `README.md`, `CHANGELOG.md` exist; nothing under `extraction/` is referenced by shipped code.
10. A proposal repo onboarded with `document.type: proposal` gets a clear "not supported in v0.1" message.

Added by this design:

11. `python3 -m pytest tests/` passes on r2d2, and every script has a falsification test.
12. The SessionStart injection stays under 10,000 characters on the traces repo (asserted by a test over the eager rules plus a representative config).

## 17. Decisions taken in this design (my calls, open to correction)

1. Single plugin at repo root with `source: "./"`, tramat style, rather than `plugins/ploma/`.
2. YAML config with a tested fallback loader instead of requiring PyYAML or switching to JSON.
3. Session logs gitignored; checkpoints committed.
4. Transient hook state under `<project>/.ploma/` instead of the home directory.
5. seven-pass becomes `/ploma:review --seven-pass`; promote-memory folds into `/ploma:learn --promote`; data-analysis ships as a project-skill template, not a plugin skill.
6. `notify.sh` dropped; statusline offered by onboard as a template.
7. Peeves and paper types split across generic, discipline and venue files; the social-science paper types survive in their own card.
8. Model routing applied in agent frontmatter (opus for editor, referees, domain-reviewer, claim-verifier; sonnet for proofreader, code-reviewer, verifier).
9. Required commit-gate checks are compile, bib and consistency; claims and proofread are recommended.
10. Project-local overrides live in `ploma.d/`.
11. Doctor makes no network calls; citation API reachability is checked by `validate-bib --semantic` itself.
12. The consistency gate entry is produced by `/ploma:commit` running the script when needed, so papers without a pipeline can pass the gate.
13. The 80/90/95 quality scores are dropped; the gate is per-check.
14. Doctor has an INFO status; optional linters are SKIP and figure provenance is INFO by default, so AC3's READY is reachable.

## 18. What is left to the builder

- Exact wording of every SKILL.md, keeping each under 500 lines with `references/` for long protocols.
- The eager rules text, within the character budget.
- The `_yamlmini.py` subset and its error messages.
- The per-section page map heuristic when `pdftotext` headings are ambiguous.
- Eval prompts and rubric wording.
- The exact slop phrase list (seeded from the style memory: no "delve", "leverage", "it is worth noting", "in this paper we", "crucial", and sentence-level em-dashes).
