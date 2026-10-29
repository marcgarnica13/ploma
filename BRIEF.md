# BRIEF: design and build `ploma`, a Claude Code harness for LaTeX academic papers

**From:** session `traces-16` (Marc's paper repo, host with TeX Live) **To:** session `papers-controller` (host `r2d2`, `/home/mgarnica/papers`)
**Date:** 2026-10-29 **Status of this repo:** SEED. Nothing at the root is final except this brief. Everything under `extraction/` is raw input for you and is meant to be deleted once ported.

## 0. The ask, in Marc's words (paraphrased faithfully)

Build a Claude Code **plugin** that, no matter the actual content of a paper (always LaTeX), helps with **brainstorming, grilling, setting up, writing, validating and formatting** academic papers. It must be installable in any paper repo with `/plugin marketplace add marcgarnica13/ploma` and `/plugin install ploma@ploma`, expose a first `/ploma:onboard` skill, and after that recommend and drive a workflow. Marc's reference for what "harness" means is **lisa** (CodySwannGT/lisa) and his own **tramat** plugin: intent captured up front, state of the art consulted, self-verification with evidence, state files that survive sessions, a doctor, and bounded loops that escalate instead of spinning. The main design and implementation happens in **your** session. `traces-16` extracted everything, will review your spec and plan, and will test the plugin on a real paper with a real TeX toolchain.

## 1. Decisions already taken with Marc (do not reopen)

| Topic | Decision |
|---|---|
| Name | `ploma` (Catalan: quill). Repo `marcgarnica13/ploma`, plugin `ploma`, skills `/ploma:<skill>`. |
| Visibility | Private repo for now. Licence check of upstreams before any public release (see §6). |
| Scope v0.1 | **LaTeX papers only.** Design the config and venue-profile layer so grant proposals and theses slot in later (`document.type` reserved), but ship and test only the paper lifecycle. |
| superpowers | **Soft dependency, sequenced not reimplemented.** ploma owns the paper lifecycle; it calls `superpowers:brainstorming`, `writing-plans`, `verification-before-completion` for generic discipline. `onboard`/`doctor` check it is installed and warn if not. |
| lisa, tramat | Pattern references, recorded in `UPSTREAMS.md` (tramat convention). Not dependencies. |
| academic-research-skills (ARS) | Ideas only. It is CC-BY-NC-4.0 and very large; do not vendor its text. |
| Hand-off | This seed repo. You clone it, build at the root, delete `extraction/` when ported. |

## 2. Who the user is and how they work

Marc Garnica Caparrós (GitHub `marcgarnica13`), sports-analytics and data-engineering researcher, author of the `tramat` harness. Memories recorded in his paper sessions, all of which the plugin's defaults should respect:

- **Options at every fork.** "For any type of reasoning line that you are working, or brainstorming about different directions, always prioritize asking me and showing me different options." He prefers checkpoint-based execution: pause at phase boundaries, show options with a recommended one first, explain the why.
- **Writing style for manuscripts:** short, direct, scientific sentences. No AI slop. **No sentence-level em-dashes** (a co-author rejected a plan for containing them).
- **Check disk before regenerating:** when asked "all good?", assess what exists, do not rebuild.
- **Compact, horizontal figures** to save page height. Page budget matters to him.
- **Edit only the sections being worked on**; when the agent finds contradictions it raises them as open flags for the author, it does not silently change prose.
- Token economy in the tramat sense: progressive disclosure, no full-file dumps, long work in subagents, terse output.

## 3. What exists today (the raw material)

Read `extraction/research/` first; it is the condensed inventory. Then read the originals under `extraction/traces-harness/.claude/`.

| Input | Where | What it tells you |
|---|---|---|
| Skills catalog, 20 skills, per-skill I/O, coupling, missing files, lifecycle | `research/01_skills_catalog.md` | The functional core to port and what to parameterize |
| Rules (19), agents (9), hooks (6), settings, references, contradictions | `research/02_rules_agents_hooks_catalog.md` | What is generic, what is project-bound, what is broken |
| Provenance, real usage history, pain points, referee-report format, plugin conventions on Marc's machine | `research/03_provenance_and_usage.md` | Why a plugin, what hurt in practice, formats to ingest |
| Web survey: 10 academic Claude Code repos, lisa internals, plugin docs, verification research, LaTeX tooling, 26 design ideas | `research/04_web_research_claude_code_academic.md` | State of the art to position against |
| Official plugin packaging facts (manifest, marketplace, hooks, frontmatter, eval) | `research/05_plugin_packaging_facts.md` | Hard constraints of the packaging format |
| Verbatim current harness (`.claude/**`, CLAUDE.md, .gitignore, main plan, session log, one sample of each report format) | `traces-harness/` | Source text to port |
| The grant-proposal fork of the same harness | `delphi-harness/` | Shows what changed when document type changed (compile-doc, review-proposal, funder-profiles, doc-verifier) |
| Makefile, LLNCS preamble, three `*_suggestion.tex` section rewrites, one raw referee report | `samples/` | Real inputs `onboard`, `compile`, `write` and `respond` must handle |
| tramat manifests, hooks.json, UPSTREAMS.md, README, init/doctor/help commands, core skill | `references/tramat/` | Marc's own packaging and stage-machine conventions |
| ARS mode registry, architecture, hooks, pipeline state machine | `references/academic-research-skills/` | Stage gates and reviewer-ensemble ideas (ideas only) |
| lisa doctor / agent-ready / persist-learning skills, four eager rules, inject-rules and verification-gate hooks | `references/lisa/` | Doctor contract, gap-driven onboarding, learnings ladder, Stop-hook gate, rules injection |

Headline facts from the inventory:

- Upstream of the current harness: `pedrohcgs/claude-code-my-workflow` v1.9, plus clo-author (editor and referee agents), claudeblattman (five-critic council, prompt skeleton), ARS (passport idea).
- Project facts (manuscript path, build command, env vars, four pipeline gotchas, venue, metric names) are hard-coded in about 10 files and restated in 8. The uv migration left three contradictory toolchain stories. This is the core problem `ploma.yaml` + `onboard` must remove.
- About 20 referenced files do not exist (`templates/*`, `quality_reports/passports/`, `quality_score.py`, `.claude/state/`, `check-skill-integrity.py`). `model-routing` is never applied. `cross-artifact-review` uses Cursor `globs:` syntax. Hook state lives in `~/.claude/sessions/<hash>/`, not in the project.
- Six skills were never run on the real paper (audit-reproducibility, seven-pass, devils-advocate, deep-audit, learn, promote-memory). MEMORY.md has zero entries. What was used and worked: lit-review with CoVe, validate-bib --semantic, proofread (report-only), verify-claims, review-paper default mode, plan mode with plans on disk.
- Real pain: number discrepancies between figures, tables and text blocked writing for a day; page budget was managed by hand repeatedly; figures have no link to the scripts that produced them; docs drifted from the stack; the response-to-referees draft never got past scaffold.

## 4. Target lifecycle (stage machine) and skill mapping

Stages, in the order Marc named them, with the skill that owns each. Names are proposals; keep them short.

| Stage | Skill(s) | Builds on | New or ported |
|---|---|---|---|
| 0 Install + onboard | `/ploma:onboard` | tramat init/onboard, lisa agent-ready (gap-driven, read-only inventory, propose before writing), K-Dense `scientific-writer-init` | NEW |
| 0b Health | `/ploma:doctor` | lisa-doctor contract: grouped PASS/WARN/FAIL/SKIP, one verdict READY / READY_WITH_WARNINGS / NOT_READY, read-only, never asks "proceed?" | NEW |
| 1 Brainstorm | `/ploma:brainstorm` | sequences `superpowers:brainstorming` with `research-ideation` and `lit-review` (CoVe-verified) | ported + glue |
| 2 Grill | `/ploma:grill` | mattpocock `grill-me`: one question at a time, each with a recommended answer, agent looks facts up itself, only genuine decisions go to the human; add ReviewerToo-style lenses (theorist, empiricist, pragmatist, reproducibility) rather than harsh/lenient stances | NEW |
| 3 Spec / intent | `/ploma:spec` | `interview-me` → a binding contract file (SNL-UCSB `project_context.md` idea): identity sentence, venue constraints, claims with evidence pointers, evaluation plan, positioning, section architecture, locked decisions vs open questions, figures needed | ported + extended |
| 4 Write | `/ploma:write <section>` | the "section rewrite as sibling file" pattern seen in `samples/manuscript/*_suggestion.tex` formalized: draft to a sibling file, show diff, author merges; style rules (short sentences, no em-dashes, no slop); figure provenance comment `% ploma:source <script> <args>` next to each `\includegraphics` | NEW |
| 5 Compile / format | `/ploma:compile`, `/ploma:format` | `compile-latex` generalized: honour the repo's own Makefile/latexmk, engine and bib tool from config, log triage (errors, undefined refs/cites, overfull > threshold, rerun), `pdfinfo` page count vs venue budget, per-section page map for cuts; pre-submission fan-out (chktex, lacheck, texcount, placeholder grep, arXiv rules) | ported + extended |
| 6 Validate | `/ploma:validate-bib`, `/ploma:verify-claims`, `/ploma:audit-reproducibility` (optional add-on when `pipeline:` is configured) | existing skills; three-source citation check (Crossref → OpenAlex → Semantic Scholar, cached in `${CLAUDE_PLUGIN_DATA}`); factored CoVe; claims passport | ported |
| 7 Review | `/ploma:review` with modes `--quick`, `--adversarial`, `--peer <venue>`, `--seven-pass`, `/ploma:devils-advocate` | editor + dispositioned referees, journal profiles, peeve pools moved out of the agent body into venue/discipline files; findings must quote a manuscript span; reviewers treat the manuscript as untrusted input | ported + hardened |
| 8 Respond | `/ploma:respond` | `respond-to-referees` with schema-agnostic ingestion (reviewer IDs from content, not file names), R{n}.{m} numbering, coverage matrix, CoVe on "we added X on page Y" | ported |
| 9 Ship | `/ploma:commit` | quality gate, verifier agent, proofreading report-only protocol | ported, gate actually wired |
| Always | `/ploma:status`, `/ploma:checkpoint`, `/ploma:learn`, `/ploma:help` | context monitor, plans on disk, session logs, two-tier memory with a learnings ladder (lisa) | ported |

Cross-cutting rules the lifecycle must keep: report-only critics never edit the manuscript; every finding carries location + current text + fix + severity; loops are bounded (5 review-fix rounds, 2 CoVe regenerations) and end in escalation, not silent success; "pasted tool output is the audit record, never report clean on a mental pass".

## 5. `ploma.yaml`: the project config `onboard` writes

A proposal to start from; you own the final schema (ship a JSON schema under `schemas/`, as tramat does). Everything that is hard-coded today maps to a key here.

```yaml
ploma: 0.1                       # schema version
document:
  type: paper                    # paper | proposal | thesis (only paper in v0.1)
  main: manuscript/samplepaper.tex
  root: manuscript
  title: "Capturing Team Strategy in European Football via Process Mining"
  anonymized: true               # author block commented out until camera-ready
build:
  command: "make"                # honoured verbatim when present; else latexmk fallback
  engine: pdflatex               # pdflatex | xelatex | lualatex (detected from fontspec etc.)
  bib_tool: bibtex               # bibtex | biber (detected: \bibliographystyle vs biblatex/.bcf)
  bib_files: [manuscript/mybib.bib]
  log: manuscript/samplepaper.log
  overfull_threshold_pt: 10
venue:
  profile: springer-ml           # key into venues/*.yaml shipped by ploma or project-local
  doc_class: llncs               # detected from \documentclass
  page_budget: 13                # null if unknown; compile reports pages vs budget
  cite_style: numeric            # numeric | author-year
reviews:
  dir: review                    # prior-round referee reports, any format
  glob: "review/*.md"
outputs:
  dir: quality_reports           # all ploma reports, plans, session logs, passports
style:
  sentences: short-direct
  forbid: ["sentence-level em-dash", "AI slop phrases"]
  figures: compact-horizontal
pipeline:                        # optional; enables audit-reproducibility and code review
  enabled: true
  language: python
  run_from: src
  rerun: "uv run python notebooks/discovery/parse_statsbomb_matches.py"
  outputs_dir: src/results
  metric_keys: [avg_fitness, generalization, dependency]
  env_contract: [MONGO_USER, MONGO_PWD, MONGO_STR, TAGS_FILE, RESULTS_FILE, STATSBOMB_DATA_DIR]
  gotchas:                       # free text, injected into reviewer context
    - "TAGS_FILE is read at import time in parsers/soccerlogs.py"
    - "Activity key format action##zone must be preserved"
    - "Pitch coordinates are flipped (y -> FIELD_WIDTH - y); verify orientation"
  tolerances: {counts: exact, metrics: 0.01, aggregates: 0.02, percentages_pp: 0.1}
dependencies:
  superpowers: soft              # doctor warns if missing
```

`onboard` behaviour to aim for: read-only inventory first (main tex via `\documentclass` search, Makefile/latexmk, bib tool, class, figures, reviews dir, results dir, git remote), propose the YAML plus the files it will write, write only after approval, be idempotent on re-run (absorb answered gaps, never clobber hand edits), record an apply receipt. Files it writes into the project: `ploma.yaml`; a marker-delimited section in `CLAUDE.md`; path-scoped rules into `.claude/rules/ploma-*.md` (plugins cannot ship rules); `quality_reports/` scaffolding; `.gitignore` entries. Ask only for what cannot be derived by reading harder (lisa's gap rule).

## 6. Dependencies, licences, upstreams

- **superpowers**: soft dependency (see §1). On r2d2 it is `superpowers@claude-plugins-official` 7.0.0; on Marc's paper host it is `superpowers@superpowers-marketplace` 5.1.0. Do not hard-pin a marketplace name; detect either.
- **lisa**: MIT. Take patterns: doctor contract, `rules/eager` injected by a SessionStart/SubagentStart hook into `additionalContext` (plugins cannot ship `rules/`), Stop-hook verification gate on a structured verdict file with a bounded block counter, learnings ladder, agent-ready gap file, "never delete a hook target mid-session" (issue #4335).
- **tramat**: Marc's own, Apache-2.0. Take: `plugin.json` + `marketplace.json` shape with `source: "./"`, `hooks/hooks.json` with `${CLAUDE_PLUGIN_ROOT}`, `UPSTREAMS.md`, `schemas/*.schema.json`, `scripts/doctor.py` pattern, tests under `tests/`, reference example instead of frozen templates.
- **ARS**: CC-BY-NC-4.0. Ideas only: stage gates that block on SUSPECTED, reviewer seats blind to each other, devil's-advocate CRITICALs adjudicated visibly, mode registry as single source of truth, manuscript treated as untrusted input.
- **pedrohcgs/claude-code-my-workflow** and **hugosantanna/clo-author**: the text we are porting descends from them. Licences were not checked. Before any public release, check both and credit in `UPSTREAMS.md`. While private, carry the existing attribution comments forward.
- **Citation APIs**: Crossref (polite pool via `mailto`), OpenAlex (keyless 10 r/s), Semantic Scholar. Use plugin `userConfig` for `mailto`/keys, cache in `${CLAUDE_PLUGIN_DATA}`. Consider wrapping `bibsleuth` instead of reimplementing existence checks.

## 7. Packaging constraints (from the official docs, verified 2026-10-29)

- Layout: `.claude-plugin/plugin.json` (+ `marketplace.json` in the same repo with `source: "./"`), `skills/<name>/SKILL.md`, `agents/*.md`, `hooks/hooks.json`, `scripts/` (not `bin/`, which claude.ai refuses), optional `.mcp.json`. `claude plugin validate . --strict` in CI.
- Names: kebab-case, must not start with `claude-`, `anthropic-`, `cc-plugin-`. Marketplace entry name must equal manifest name. Install string will be `/plugin install ploma@ploma`.
- **Plugins cannot ship `rules/` or a CLAUDE.md.** Always-on guidance goes through a SessionStart hook `hookSpecificOutput.additionalContext` (10,000 char cap) or through files `onboard` writes into the project.
- Skill frontmatter available: `description`, `argument-hint`, `disable-model-invocation`, `user-invocable`, `allowed-tools`, `model`, `effort`, `context: fork` + `agent`, `paths`, `hooks`. `context: fork` is a frontmatter field, not a Task parameter; the current harness misuses it in six skills.
- Agent frontmatter inside plugins ignores `permissionMode`, `hooks`, `mcpServers`.
- Hooks: `hooks/hooks.json`, events include SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, Stop, PreCompact, PostCompact, SubagentStart/Stop. Stop can block with exit 2 or `{"decision":"block"}` and receives `last_assistant_message`.
- Versioning: bump `version` in `plugin.json` per release or omit it to track commits. Private repo install works through the user's own git credentials (SSH key or `gh auth setup-git`). Note: on Marc's paper host SSH to github.com hangs; HTTPS via `gh auth setup-git` works, so document the HTTPS path.
- Testing: `claude plugin eval` (v2.1.269+) with `evals/<case>/prompt.md` and graders; `/skill-doctor` for never-fired skills; `/doctor prompt-audit` for contradictions.
- r2d2 has **no TeX toolchain**. Structure-test compile/format there; `traces-16` runs them for real.

## 8. Pain points and what v0.1 must do about each

| Observed pain | v0.1 answer |
|---|---|
| Numbers disagreed between figure, table and text; blocked writing | Claims passport (`quality_reports/passports/<slug>.yaml`) populated by `audit-reproducibility` and checked by a deterministic internal-consistency pass (text vs tables vs `outputs_dir`), wired into `/ploma:commit` |
| Page budget managed by hand, limit changed several times | `compile` reports pages vs `venue.page_budget` and a per-section page map; `format` proposes cut plans ordered by value per page (the `page_budget_cut_proposal.md` sample shows the format Marc accepted) |
| Figures have no link to the scripts that made them | `% ploma:source` provenance comments; `doctor` warns on figures without one when `pipeline.enabled` |
| Docs drifted from the stack after a migration | single `ploma.yaml`; rules and agents read it instead of restating facts; `doctor` flags drift |
| Skills existed but were never run; MEMORY.md stayed empty | `/ploma:help` and the SessionStart status line recommend the next stage from state; learnings ladder with human-gated promotion |
| Referee reports arrive in arbitrary formats with wrong file numbering | `respond` ingests any text/pdf/docx, extracts reviewer IDs from content, numbers R{n}.{m}, keeps a coverage matrix |
| Response-to-referees stalled at scaffold | `respond` produces the full document with CoVe on location claims, and a `--audit` mode for an existing draft |
| Contradictory thresholds and loops scattered across rules | one `rules/eager/limits.md` (quality gates 80/90/95, loop caps, tolerances) injected at session start |

## 9. Acceptance criteria for v0.1

1. `claude plugin validate . --strict` passes; `/plugin marketplace add marcgarnica13/ploma` + `/plugin install ploma@ploma` works on both hosts.
2. `/ploma:onboard` on the traces paper (`manuscript/samplepaper.tex`, LLNCS, Makefile, bibtex, `review/*.md`, `src/results/`) proposes a correct `ploma.yaml` with zero wrong detections and writes files only after approval.
3. `/ploma:doctor` returns READY on traces after onboarding and NOT_READY with actionable findings on an empty repo.
4. `/ploma:compile` reproduces today's `make` result and reports overfull boxes, undefined references and page count vs budget. (Run by `traces-16`.)
5. `/ploma:validate-bib --semantic` and `/ploma:verify-claims` reproduce the two existing PASS reports in `extraction/traces-harness/quality_reports/sample_outputs/`.
6. `/ploma:review --peer springer-ml` produces desk review, two referee reports and an editorial decision in the same structure as today, with no soccer-specific text left in agent bodies.
7. `/ploma:respond extraction/samples/review/review1.md` yields a numbered concern list with reviewer IDs read from content.
8. `/ploma:grill` runs one question at a time with recommended answers and ends with a written decision log.
9. `evals/` has at least one case per lifecycle skill; `UPSTREAMS.md`, `README.md`, `CHANGELOG.md` exist; no file under `extraction/` is referenced by shipped code.
10. A second repo type (`delphi_nba` proposal) can be onboarded with `document.type: proposal` producing a clear "not supported in v0.1" message rather than wrong behaviour.

## 10. How we work together

1. You clone this repo, read this brief and `extraction/research/01-05`, then run `superpowers:brainstorming` → write the spec under `docs/superpowers/specs/` → `superpowers:writing-plans`.
2. Before implementing, send the spec and plan summary to `traces-16` (SendMessage) and keep Marc in the loop with options at the forks (he decides direction; see §2).
3. Implement with subagent-driven development and small commits on `main` (private repo; branches optional).
4. When `onboard`, `doctor`, `compile` and `validate-bib` exist, ping `traces-16`; it installs the plugin into the traces paper repo, runs them with real TeX, and reports defects back.
5. `traces-16` keeps `extraction/` authoritative until you say it is fully ported; after that, delete it in one commit.
