# Skills catalog of the traces academic harness (extracted 2026-10-29)

Source: `/home/marc/Development/dshs/mlsa/traces/.claude/skills/` (20 skills). Produced by an Explore agent for the ploma hand-off. Verbatim copies of the skills live in `extraction/traces-harness/.claude/skills/`.

Abbreviations used below: **MS** = `manuscript/samplepaper.tex`, **QR** = `quality_reports/`, **PFV** = the Post-Flight Verification protocol in `.claude/rules/post-flight-verification.md` (Chain-of-Verification, or CoVe: spawn `claim-verifier` with `subagent_type=claim-verifier, context=fork` and don't pass it the draft; outcome is PASS, PARTIAL or FAIL; on FAIL, regenerate up to 2 attempts).

## Problems that apply to all 20 skills (summarized)

- **The `context=fork` instruction probably does nothing.** Six skills tell the model to call `Task` with `context=fork` or `context: fork`. That is a skill-frontmatter field, not a `Task` parameter, and no skill sets `context: fork` in its own frontmatter. So the "fresh context" isolation the verification design relies on likely only comes from subagents starting empty. Worth confirming before relying on it.
- **No skill sets `model:`.** All 9 agents are `model: inherit`, except `promote-memory-council`, which is `haiku`. That conflicts with `.claude/rules/model-routing.md`, which says Opus for `editor`, the referees and `claim-verifier`. Only 3 skills set `effort: high`: `audit-reproducibility`, `respond-to-referees` and `seven-pass-review`. `model-routing.md` also says `/deep-audit` ships at `effort: high`, but it doesn't.
- **Six skills are missing from the project listings.** `checkpoint`, `commit`, `compress-session`, `context-status`, `learn` and `promote-memory` don't appear in `CLAUDE.md` or `.claude/WORKFLOW_QUICK_REF.md`. Only 14 of the 20 are listed, the same drift `/commit` Step 0b is meant to catch.
- **Five skills are hidden from the model** with `disable-model-invocation: true`: `checkpoint`, `compress-session`, `deep-audit`, `learn`, `promote-memory`. `context-status` is not hidden.

---

## 1. Per-skill catalog

### 1.1 `audit-reproducibility`
1. **Description:** Cross-checks numeric claims in the manuscript against the Python pipeline outputs and reports PASS/FAIL per claim against tolerances. **Args:** `[manuscript path] [outputs-dir]` (defaults: MS, `src/results/`). `effort: high`. Tools: Read, Grep, Glob, Write, Bash, Task, Monitor.
2. **Workflow:**
   - Phase 0 pre-flight: read the tolerances; check the outputs dir exists and isn't stale; check the environment is captured.
   - Phase 1: extract claims (metrics, table cells, counts, summary stats, percentages) to JSON.
   - Phase 2: pull results from outputs in priority order: json, csv, `.tex`, pkl/parquet, run logs.
   - Phase 3: fuzzy-match claims to results; confidence below 0.7 means UNMATCHED.
   - Phase 4: tolerance check (integers exact; metrics <0.01; aggregate/generalization <0.02; percentages ±0.1pp).
   - Phase 5: report. Exit 0 if all pass, 1 on any FAIL, 0 with a warning if anything is UNMATCHED.
   - **Passport mode** (labelled v1.9.0): if `QR/passports/<slug>.yaml` exists, it updates each claim's status in place (PASS/FAIL/STALE/UNVERIFIED). It never deletes entries.
   - Optional: re-run the pipeline in the background and watch it with Monitor.
3. **Agents:** none spawned directly (`Task` is allowed but unused). No fork.
4. **Reads:** MS, `src/results/<run>/` (metrics.json, csv, parquet, pkl), `src/requirements.txt`, `.claude/rules/replication-protocol.md`, `QR/passports/<paper-slug>.yaml`.
   **Writes:** `QR/reproducibility_claims_[manuscript-name].json`, `QR/reproducibility_audit_[manuscript-name].md`, passport YAML in place.
5. **Cites:** `rules/replication-protocol.md`, `agents/python-reviewer.md`, `skills/review-paper`.
6. **TO-PARAMETERIZE:**
   - Default paths: MS, `src/results/`, the example dir `src/results/offensive_statsbomb_pass_09x/`.
   - Pipeline entry point: `python notebooks/discovery/parse_statsbomb_matches.py`, run from `src/` with the env-var contract.
   - "MongoDB caveat" / Mongo data snapshot, mentioned repeatedly.
   - Metric names: `avg_fitness`, `generalization`, `dependency`.
   - Examples: "12,430 offensive possessions", "64 matches", "38% of possessions reach the box", "Offensive net".
   - A whole "Process-mining notes" section (result-dir name encodes source and dependency threshold, e.g. StatsBomb at 0.9).
   - `src/requirements.txt`.
   - Tolerance table copied inline here; it also lives in `replication-protocol.md`, so the two can drift.
   - The `.json → .csv → .tex → pkl` lookup order assumes a Python pipeline.
7. **Missing:**
   - `src/results/offensive_statsbomb_pass_09x/`: the closest real dirs are `offensive_statsbomb_pass_09`, `_095` and `_099`.
   - `QR/passports/` does not exist.
   - Note that `src/results/` exists but is gitignored.
8. **Provenance:** "Passport-mode (v1.9.0)" is an upstream template version label. Passport concept credited, in `replication-protocol.md:179`, to `github.com/Imbad0202/academic-research-skills`.

### 1.2 `checkpoint`
1. **Description:** Saves a structured state snapshot: plan, decisions, `path:line` pointers, open questions, next 1–3 actions. **Args:** `[short-topic-slug] [--no-memory]`. `author: Claude Code Academic Workflow`, `version: 1.0.0`, `disable-model-invocation: true`. Tools: Read, Write, Bash.
2. **Workflow:**
   - Phase 1, gather: latest plan, latest session log, MEMORY.md, git log/status/branch, `git diff --stat`, TodoWrite list.
   - Phase 2: write the checkpoint (under ~80 lines).
   - Phase 3: propose 0–3 `[LEARN]` entries; append to MEMORY.md only with approval. Machine-specific ones go to `.claude/state/personal-memory.md`.
   - Phase 4: print a summary.
3. **Agents:** none.
4. **Reads:** `QR/plans/*.md`, `QR/session_logs/*.md`, `.claude/MEMORY.md`, git.
   **Writes:** `QR/checkpoints/YYYY-MM-DD_<slug>.md`, MEMORY.md (with approval).
5. **Cites:** `rules/session-logging.md`, `rules/plan-first-workflow.md`, `rules/meta-governance.md`, `hooks/pre-compact.py` (`CLAUDE_PRECOMPACT_BLOCK_ON_DRAFT=1`, which does exist at `pre-compact.py:152`), `templates/decision-record.md`.
6. **TO-PARAMETERIZE:** nothing domain-specific. Upstream leftovers in the examples: `v180-polisci`, branch `feat/v1.8.0-polisci-apr2026`, `CHANGELOG.md` "v1.8.0 entry", `methods-referee.md` / `journal-profiles.md` "poli-sci block".
7. **Missing:** `templates/decision-record.md` (no `templates/` dir), `QR/checkpoints/`, `QR/decisions/`, `.claude/state/personal-memory.md`, `CHANGELOG.md`.
8. **Provenance:** HTML comment says the pattern was adapted from Hugo Sant'Anna's clo-author v4.2.0 (`github.com/hugosantanna/clo-author`), "used with permission", reimplemented in original prose.

### 1.3 `commit`
1. **Description:** Stage, commit, push, open a PR and merge to main. Only on explicit intent. **Args:** `[optional: commit message]`. Tools: Bash, Read, Glob, Task.
2. **Workflow:**
   - Step 0 quality gate: rubric score from `quality-gates.md`. For `.tex`, run `cd manuscript && make` with a clean log. For `.py`, run the `python-reviewer` agent. Halt below 80 unless the user says "commit anyway". Spawn the `verifier` agent.
   - Step 0b surface-sync: if `.claude/` inventory changed, check skill/agent/rule/hook counts in CLAUDE.md, WORKFLOW_QUICK_REF and MEMORY.md.
   - Steps 1–7: status, new branch, `git add` specific files (never `-A`), commit (`$ARGUMENTS` used verbatim), push, `gh pr create`, `gh pr merge --merge --delete-branch`, checkout main, pull, report.
3. **Agents:** `verifier`, `python-reviewer` (via Task). No fork.
4. **Reads:** git diff, changed `manuscript/*.tex`, `src/**/*.py`. **Writes:** git commits and PRs. No QR output.
5. **Cites:** `rules/quality-gates.md`, `references/audit-pet-peeves.md` (peeves #7 and #18).
6. **TO-PARAMETERIZE:**
   - `manuscript/*.tex`, `cd manuscript && make`, `src/**/*.py`, `python-reviewer`.
   - Hard-coded `main` branch and the `--merge` strategy.
   - PR body footer is fixed text.
   - Never invokes `/audit-reproducibility`, `/verify-claims` or the passport, even though `replication-protocol.md` and `verify-claims` say `/commit` gates on them.
7. **Missing:**
   - No scoring script: the 80/90/95 thresholds are applied by hand by the model.
   - `--strict-passport` (from `replication-protocol.md`) and `verifyClaims.allowHighWarn` (from `verify-claims`) are not in `settings.json`.
   - `/commit` implements neither gate.
8. **Provenance:** none.

### 1.4 `compile-latex`
1. **Description:** Compile with pdflatex via the Makefile (pdflatex → bibtex → pdflatex ×2). **Args:** none ("builds manuscript/samplepaper.tex"). Tools: Read, Bash, Glob.
2. **Workflow:**
   - `cd manuscript && make` (also `make clean` / `make cleanall`).
   - Grep `samplepaper.log` for Overfull hbox, undefined citation/reference, "Label(s) may have changed".
   - `xdg-open` the PDF.
   - Report: success, overfull count, undefined refs, rerun-needed, page count.
3. **Agents:** none.
4. **Reads:** `manuscript/Makefile`, `manuscript/samplepaper.log`. **Writes:** `manuscript/samplepaper.pdf` and aux files.
5. **Cites:** none.
6. **TO-PARAMETERIZE:**
   - Main file `samplepaper.tex`, dir `manuscript/`, `make` targets.
   - "Springer LLNCS", `llncs.cls`, `splncs04.bst`, `mybib.bib`, `fig1-5.pdf`.
   - "never xelatex" and pdflatex-only.
   - Overleaf note.
   - Anonymization note (author block commented out).
   - Linux-only `xdg-open`.
   - The engine and bibtex/biber choice should come from config.
7. **Missing:** nothing. Makefile, `llncs.cls`, `splncs04.bst`, `mybib.bib`, `fig1.pdf` and `fig5.pdf` all exist.
8. **Provenance:** none.

### 1.5 `compress-session`
1. **Description:** Distils the conversation into a structured note before auto-compaction. **Args:** `[optional-topic-slug]`. `author: Claude Code Academic Workflow`, `version: 1.0.0`, `disable-model-invocation: true`. Tools: Read, Write, Glob, Grep, Bash.
2. **Workflow:**
   - Step 1: read the latest session log.
   - Step 2: distil into these sections: Active state, Decisions, Files touched, Open questions, Next actions (1–3), "Discarded as noise", Proposed `[LEARN]`.
   - Step 3: save.
   - Step 4: summarize.
   - Includes an optional PreCompact hook JSON snippet (reminder only, no auto-invoke).
3. **Agents:** none.
4. **Reads:** `QR/session_logs/`, `QR/plans/`, git. **Writes:** `QR/session_logs/YYYY-MM-DD_compression_<topic>.md` (gitignored; confirmed at `.gitignore:50`).
5. **Cites:** `rules/session-logging.md`. Links Drew Breunig's "How Long Contexts Fail" (dbreunig.com). Mentions `/checkpoint`, `/context-status`, `/promote-memory`, the Stop hook.
6. **TO-PARAMETERIZE:** none domain-specific; claims a "200-line MEMORY.md cap".
7. **Missing:** none critical.
8. **Provenance:** template author tag only.

### 1.6 `context-status`
1. **Description:** Show context usage and session health. No args. `author: Claude Code Academic Workflow`, `version: 1.0.0`. Tools: Read, Bash, Glob.
2. **Workflow:**
   - Step 1: `cat ~/.claude/sessions/*/context-monitor-cache.json` (written by `hooks/context-monitor.py:73`).
   - Step 2: `ls` plans.
   - Step 3: `ls` session logs.
   - Step 4: formatted status block (pre-compact and post-compact restore hooks configured?).
3. **Agents:** none.
4. **Reads:** `~/.claude/sessions/*/context-monitor-cache.json`, `QR/plans`, `QR/session_logs`. **Writes:** nothing.
5. **Cites:** none.
6. **TO-PARAMETERIZE:** none. Depends on harness hooks (`context-monitor.py`, `pre-compact.py`, `post-compact-restore.py`), which a plugin would have to ship.
7. **Missing:** nothing in the repo.
8. **Provenance:** template author tag.

### 1.7 `data-analysis`
1. **Description:** End-to-end Python analysis on the process-mining pipeline. **Args:** `[dataset/source description or analysis goal]`. Tools: Read, Grep, Glob, Write, Edit, Bash, Task, Monitor.
2. **Workflow:**
   - Phase 0: Pre-Flight Report (data source, fields, counts, schema, env contract, conventions read, plan). Stop if inputs are unreadable.
   - Phase 1: setup and loading.
   - Phase 2: EDA (counts, distributions, pitch heatmaps, sequence views).
   - Phase 3: build event log, discover the heuristic net (dependency sweep 0–0.99), held-out fitness, baseline, ablations.
   - Phase 4: tables (`.tex`/`.csv`/`.json`) and pitch figures.
   - Phase 5: save, run `python-reviewer`, fix Critical/High findings.
   - Monitor pattern for long runs.
3. **Agents:** `python-reviewer`. No fork.
4. **Reads:** Mongo, `src/sports_pm/...`, `.claude/rules/python-code-conventions.md`, `content-invariants.md` (INV-9..12). **Writes:** scripts in `src/` or `src/notebooks/discovery/[script_name].py`; outputs in `src/results/<run>/`.
5. **Cites:** `rules/python-code-conventions.md`, `rules/content-invariants.md`, `CLAUDE.md`.
6. **TO-PARAMETERIZE:** the whole skill is project-specific.
   - Concepts: process mining, possessions, pitch, Wyscout/soccerlogs, StatsBomb.
   - pm4py, `sports_pm`.
   - `TAGS_FILE`, `RESULTS_FILE`, `MONGO_*`.
   - `action##zone`, `possession_count`, 105×68 coordinates.
   - Functions: `logic/reducers.get_match_info`, `filter_offensive_sequences(_statsbomb)`, `create_event_log`, `get_heuristic_net`, `viz/image_utils.save_image`.
   - Plot classes: `MultipleEventField`, `SequenceEventField`, `HueristicField`.
   - "four documented gotchas", the stage chain "Source→Segment→Filter→Standardize→Discover→Visualize", the `parse_statsbomb_matches.py` entry point.
   - In a plugin this should become a generic "analysis-pipeline" skill reading a project config, or move to a project-local skill.
7. **Missing:** none. All named functions and classes exist (`discovery.py:18,61`, `filters.py:3,127`, `reducers.py:3`, `image_utils.py:3`, `viz/field_graph.py:155,222,319`).
8. **Provenance:** none.

### 1.8 `deep-audit`
1. **Description:** Repository infrastructure consistency audit: 4 parallel agents, fix, loop until clean. No args. `author: Claude Code Academic Workflow`, `version: 1.0.0`, `disable-model-invocation: true`. Tools: Read, Write, Edit, Bash, Glob, Grep, Task.
2. **Workflow:**
   - Phase 0 mechanical checks by hand: allowed-tools vs body parity, argument-hint vs flags, anchors, rule `paths:` vs skill.
   - Phase 1: 4 parallel `general-purpose` agents: Docs/surface; Executable code (hooks and `src/`); Skills/rules; Cross-document. Each must read `audit-pet-peeves.md`.
   - Phase 2: triage, with a known false-alarms list and a count-drift grep list.
   - Phase 3: fix.
   - Phase 4: `cd manuscript && make` if the manuscript changed.
   - Phase 5: re-audit loop, **max 5 loops**.
3. **Agents:** 4× `general-purpose` (no fork stated).
4. **Reads:** `.claude/**`, CLAUDE.md, README, `src/`, `manuscript/`. **Writes:** edits anywhere; round report in chat only, no QR file.
5. **Cites:** `references/audit-pet-peeves.md`, `rules/python-code-conventions.md`, `python-reviewer` checklist.
6. **TO-PARAMETERIZE:**
   - `manuscript/samplepaper.tex`, `src/sports_pm/...`, `cd manuscript && make`, run-from-`src/`.
   - The "`action##zone` is not a markdown heading" false alarm.
   - Gotchas: `TAGS_FILE` import, `##` key, coordinate flip, env contract.
   - Upstream history: PR #92 and #87, "Guide, README, landing page", "19 skills → 21", Claude Code issue #25380.
7. **Missing:**
   - `check-skill-integrity.py`: the skill itself says "This repo does not vendor" it.
   - README does not exist.
   - "Guide / landing page" does not exist.
8. **Provenance:** template author tag. Upstream PR numbers suggest it came from the public template repo.

### 1.9 `devils-advocate`
1. **Description:** 5–7 adversarial questions on design choices; read-only. **Args:** `[manuscript path]` (default MS). Tools: Read, Grep, Glob.
2. **Workflow:** read the target, `.claude/rules/` and `review/review1–3.md`. Generate 5–7 challenges across 7 categories (framing, method choice, evaluation, generalization, scope, argument ordering, related work). Output in a fixed format with severity and a summary verdict.
3. **Agents:** none.
4. **Reads:** MS, `.claude/rules/`, `review/review1.md`, `review2.md`, `review3.md`. **Writes:** chat only (no Write tool).
5. **Cites:** "knowledge base in `.claude/rules/`" (generic).
6. **TO-PARAMETERIZE:**
   - MS, `review/review1–3.md` (prior-round referee file naming).
   - Example challenges: "soccer application of an off-the-shelf method", "24 zones, `action##zone` key, heuristic-net discovery", "Wyscout vs StatsBomb", "process mining and sports analytics", "previous conference version".
   - "ML-general contribution" framing.
7. **Missing:** none. `review/review1–3.md` exist.
8. **Provenance:** none.

### 1.10 `interview-me`
1. **Description:** Multi-turn interview that turns a fuzzy idea into a spec. **Args:** `[brief topic or 'start fresh'] [--no-verify]`. Tools: Read, Write, Task.
2. **Workflow:**
   - Six phases, asking 1–2 questions at a time in plain text. It explicitly says not to use AskUserQuestion. Phases: Big picture (plus paper type), Motivation, Data, Method & Evaluation, Expected results, Contribution. Usually 5–8 exchanges.
   - Writes the Research Specification.
   - PFV if the spec cites papers.
   - An ADR-style decision record for each contested choice.
3. **Agents:** `claim-verifier` (fork).
4. **Reads:** `agents/methods-referee.md`, `references/discipline-cards.md`, `master_supporting_docs/`. **Writes:** `QR/research_spec_[sanitized_topic].md`, `QR/decisions/YYYY-MM-DD_[short-topic].md`.
5. **Cites:** `rules/post-flight-verification.md`, `agents/methods-referee.md`, `references/discipline-cards.md`.
6. **TO-PARAMETERIZE:**
   - Paper-type list "empirical-ML/computational-pipeline | methods | benchmark | application".
   - "Wyscout / StatsBomb via Mongo", competitions/seasons/matches.
   - "heuristic-net discovery over offensive possession traces", "conformance fitness", ablations "zone granularity, segmentation rule, dependency threshold", "tactically".
   - Econ leftovers: "the CPS has field `educ_attain`", "Smith (2019, *JEL*)".
7. **Missing:** `master_supporting_docs/`, `QR/decisions/`.
8. **Provenance:** none. `deep-audit` mentions a "/interview-me miss on PR #92", which points to the upstream template.

### 1.11 `learn`
1. **Description:** Turns session discoveries into a new skill. **Args:** `[skill-name (kebab-case)]`. `author: Claude Code Academic Workflow`, `version: 1.0.0`, `disable-model-invocation: true`. Tools: Read, Write, Bash, Glob, Grep.
2. **Workflow:** Phase 1 self-assessment (4 questions); Phase 2 dedupe against `.claude/skills/`; Phase 3 write the SKILL.md template; Phase 4 quality checklist; report.
3. **Agents:** none.
4. **Reads:** `.claude/skills/`. **Writes:** `.claude/skills/[name]/SKILL.md`.
5. **Cites:** CLAUDE.md, MEMORY.md (in the example).
6. **TO-PARAMETERIZE:** the whole worked example: `tags-file-import-guard`, `src/sports_pm/parsers/soccerlogs.py`, `TAGS_FILE`, `tags2name.csv`, `author: traces project`, `[LEARN:env]`.
7. **Missing:**
   - `/learn --revoke`, cited by `promote-memory`, is not implemented here.
   - The example's file paths do exist.
8. **Provenance:** template author tag.

### 1.12 `lit-review`
1. **Description:** Structured literature search and synthesis with BibTeX. **Args:** `[topic...] [--no-verify]`. Tools: Read, Grep, Glob, Write, WebSearch, WebFetch, Task.
2. **Workflow:**
   - Parse the topic.
   - Search `master_supporting_docs/supporting_papers/`, WebSearch, WebFetch and the existing `.bib`.
   - Organize into 4 categories; find gaps; extract BibTeX; save.
   - Mandatory PFV, skipped with `--no-verify` or when the user supplies ≤3 papers they've already read.
3. **Agents:** `claim-verifier` (fork).
4. **Reads:** `master_supporting_docs/supporting_papers/`, any `.bib`. **Writes:** `QR/lit_review_[sanitized_topic].md`. An existing example is `QR/lit_review_process-mining-soccer-2023-2026.md`.
5. **Cites:** `rules/post-flight-verification.md`.
6. **TO-PARAMETERIZE:** "process mining + sports analytics" (open debates), example "van der Aalst (2016)". Otherwise mostly generic.
7. **Missing:** `master_supporting_docs/supporting_papers/`.
8. **Provenance:** none.

### 1.13 `promote-memory`
1. **Description:** A five-critic council votes on `[LEARN]` entries in personal memory; 3 of 5 votes promotes. **Args:** `[entry-substring or 'all']`. `author: Claude Code Academic Workflow`, `version: 1.0.0`, `disable-model-invocation: true`. Tools: Read, Write, Glob, Grep, Task, Bash.
2. **Workflow:**
   - Read candidates.
   - Spawn 5 critics in parallel (Generality, Staleness, Redundancy, Evidence, Format), Haiku tier, `context: fork`.
   - Aggregate (5 = promote, 4 = with note, 3 = after fixes, ≤2 = reject).
   - Present; the user approves; write.
   - Never auto-promotes or demotes.
3. **Agents:** `promote-memory-council` (one agent file, five roles; `model: haiku`), 5× fork.
4. **Reads:** `.claude/state/personal-memory.md`, MEMORY.md, CLAUDE.md, rules. **Writes:** MEMORY.md, personal-memory.md (marked promoted), `QR/memory_promotion_<date>.md`.
5. **Cites:** `rules/meta-governance.md`, `agents/promote-memory-council.md`, `rules/model-routing.md`.
6. **TO-PARAMETERIZE:** domain-neutral. Econ leftovers: "non-econ forker", `[LEARN:r-code]` example. Suggests `/loop monthly`.
7. **Missing:** `.claude/state/` and `personal-memory.md` (the skill has no input), `/learn --revoke`.
8. **Provenance:** HTML comment says adapted, with attribution, from Chris Blattman's claudeblattman v2.1 "Five-critic council" (claudeblattman.com, Apr 2026). The repo also references `github.com/chrisblattman/claudeblattman` in `references/prompt-formatting-core.md`.

### 1.14 `proofread`
1. **Description:** Read-only proofreading report. **Args:** `[filename or 'all']` (default MS). Tools: Read, Grep, Glob, Write, Task.
2. **Workflow:** pick files; launch a `proofreader` agent per file (grammar, typos, overflow, consistency, academic quality); report each finding with location, current text, fix and severity; save; never edit; summarize.
3. **Agents:** `proofreader` (no fork).
4. **Reads:** `manuscript/*.tex`, the pdflatex log. **Writes:** `QR/FILENAME_report.md`. An existing example is `QR/samplepaper_report.md`.
5. **Cites:** none explicitly. `rules/proofreading-protocol.md` exists and is implied by "mandatory proofreading protocol".
6. **TO-PARAMETERIZE:** `manuscript/`, MS, `\cite{...}` convention.
7. **Missing:** none.
8. **Provenance:** none.

### 1.15 `research-ideation`
1. **Description:** One-shot research questions, hypotheses and strategies. **Args:** `[topic...] [--no-verify]`. Tools: Read, Grep, Glob, Write, WebSearch, WebFetch, Task.
2. **Workflow:** understand the input; 3–5 research questions from descriptive to application; tag paper type; per question give hypothesis, method/evaluation, data, assumptions, pitfalls, literature; rank; save; mandatory PFV.
3. **Agents:** `claim-verifier` (fork).
4. **Reads:** `master_supporting_docs/`, `.claude/rules/`, `agents/methods-referee.md`, `references/discipline-cards.md` (the `ml` card). **Writes:** `QR/research_ideation_[sanitized_topic].md`.
5. **Cites:** `rules/post-flight-verification.md`, `methods-referee.md`, `discipline-cards.md`.
6. **TO-PARAMETERIZE:**
   - Every example: "process-mining offensive build-up play", zone-transition, fitness vs shots/goals, StatsBomb via Mongo, MongoDB-snapshot pitfall, StatsBomb `obv_total_net`, pm4py alignment fitness.
   - Paper-type taxonomy.
   - **Econ leftover:** "Suggest specific datasets (FRED, Census, PSID, administrative data)". Also the RQ ladder labelled "descriptive to causal".
7. **Missing:** `master_supporting_docs/`.
8. **Provenance:** none.

### 1.16 `respond-to-referees`
1. **Description:** Response-to-referees document mapping each comment to its revision. **Args:** `[referee-report-path] [revised-manuscript-path] [--no-verify]`. `effort: high`. Tools: Read, Write, Edit, Grep, Glob, Bash, Task.
2. **Workflow:**
   - Step 0: convert pdf/docx/html with `pdftotext`, `pandoc` or `docx2txt` into a `mktemp` file.
   - Step 1: parse concerns as R{n}.{m}.
   - Step 2: locate each in the manuscript.
   - Step 3: classify (Addressed, Partially, Deferred, Disagreement, or UNADDRESSED).
   - Step 4: draft responses of 3–6 sentences.
   - Step 5: write the document from a template.
   - Step 5.5: mandatory PFV on "we added X on page Y" claims.
   - Step 6: warning summary in chat.
   - Final verification checklist.
3. **Agents:** `claim-verifier` (fork).
4. **Reads:** referee report (would be `review/review1–3.md` here, but nothing is hard-coded), revised manuscript, `templates/response-to-referees.md`. **Writes:** `response-to-referees.md` (repo root or user path), optional `response-to-referees-matrix.csv`, optionally QR. An existing example is `QR/response_to_referees_draft.md`.
5. **Cites:** `rules/post-flight-verification.md`, `skills/review-paper` (`--peer --r2`), `/seven-pass-review`, `domain-reviewer`.
6. **TO-PARAMETERIZE:** little domain wording. The output path is inconsistent: repo root by default, QR "if you want a permanent record". The journal and manuscript ID come from the header.
7. **Missing:** **`templates/response-to-referees.md`**, the required output structure (no `templates/` dir).
8. **Provenance:** none.

### 1.17 `review-paper`
1. **Description:** Manuscript review in 3 modes. **Args:** `[paper path] [--adversarial | --peer <journal> [--r2 | --r3 | --stress | --variance N] [--no-novelty-check]] [--no-cross-artifact]`. Tools: Read, Grep, Glob, Write, Edit, Bash, Task. (WebSearch is **not** in allowed-tools even though the editor does novelty probes; the forked editor agent would need it.)
2. **Workflow:**
   - **Default:** locate the paper (default MS, glob `manuscript/*.tex`); read it; score 6 dimensions; give 3–5 referee objections; write the report.
   - Step 6b cross-artifact: auto-invoke `/audit-reproducibility` if figures or outputs trace back to `src/`.
   - **`--adversarial`:**
     - Phase 0: compile, then snapshot (git stash or `.review-backup/`).
     - Critic, then fixer (user approves edits, recompile), then fresh `general-purpose` re-audit.
     - **Max 5 rounds.** A concern repeating in round N and N+2 counts as author disagreement.
     - Spend cap ~500k tokens; roll back on compile failure.
   - **`--peer <J>`:**
     - Phase 0: `/audit-reproducibility`, then Pre-Flight Report.
     - Phase 1: editor desk review with novelty probe (WebSearch), then PFV via `claim-verifier`. Outcome is DESK REJECT or SEND OUT.
     - Phase 1b: 2 dispositions drawn from 6 (METHODOLOGY-RIGOR, REPRODUCIBILITY, NOVELTY-RELATED-WORK, EVALUATION-VALIDITY, CLARITY-PRESENTATION, SKEPTIC), plus peeves.
     - Phase 2: `domain-referee` and `methods-referee` in parallel, forked.
     - Phase 3: editor synthesis (FATAL / ADDRESSABLE / TASTE).
     - Phase 4: summary.
   - **`--r2` / `--r3`:** reload the prior round; hard cap r3.
   - **`--stress`:** SKEPTIC ×2, doubled peeves.
   - **`--variance N`:** default 3, max 5, at least one SKEPTIC when N≥3. Cannot be combined with `--stress` or `--r2`/`--r3`.
3. **Agents:** `editor`, `domain-referee`, `methods-referee` (fork); `claim-verifier` (fork); `general-purpose` (fresh re-audit); calls the `/audit-reproducibility` skill.
4. **Reads:** MS, `.claude/references/journal-profiles.md`, `src/**/*.py`, `src/results/`, `fig1-5.pdf`, `%% source:` comments, passport.
   **Writes:**
   - `QR/paper_review_[name]_round[N].md` and `QR/paper_review_[name]_FINAL.md`.
   - `QR/peer_review_[paper]/{desk_review, referee_domain, referee_methods, editorial_decision}.md` (plus `_r2`, ...).
   - Variance mode: `QR/peer_review_<paper>/{referee_1..N, decision_distribution, editor_synthesis}.md`.
   - `QR/cross_artifact_[paper]/{reproducibility.md, python_review_*.md}`.
   - `.review-backup/`.
5. **Cites:** `references/journal-profiles.md`, `agents/editor.md`, `domain-referee.md`, `methods-referee.md`, `rules/cross-artifact-review.md`, `rules/post-flight-verification.md`, AgentReview (arXiv:2406.12708), the workflow guide's "Cost-Conscious Composition".
6. **TO-PARAMETERIZE:**
   - "Springer Machine Learning journal" in the description and Principles.
   - Journal short names `ML` and `MLCONF`.
   - The Method Soundness dimension hard-codes the pipeline: segmentation → offensive filter → 24-zone → heuristic net → conformance fitness, plus `action##zone`.
   - Evaluation dimension: "Wyscout vs StatsBomb", "same-match possessions", "fitness value tactically".
   - Paper-type default `empirical-ML / computational-pipeline`.
   - MS, `manuscript/*.tex`, `cd manuscript && make`, `fig1-5.pdf`, `src/results/`.
   - The 6 dimensions and 6 dispositions are general and worth keeping.
7. **Missing:**
   - The "Workflow guide / Cost-Conscious Composition" section is not in the repo.
   - `python_review_*.md` is claimed to come "via /audit-reproducibility", but `audit-reproducibility` doesn't produce it.
   - Passport.
   - The adversarial-mode "with Edit / Edit tools" is a typo.
   - Note: `journal-profiles.md` does contain `ML`, `MLCONF` and a profile template (lines 35, 83, 145).
8. **Provenance:** the agents are "adapted from Hugo Sant'Anna's clo-author (`https://github.com/hugosantanna/clo-author`) with permission". `--variance` cites AgentReview (ACL 2024). The v1.7.0 label on the novelty-probe Post-Flight is an upstream template version.

### 1.18 `seven-pass-review`
1. **Description:** Mechanizes "Pattern 15": 7 parallel forked lenses, then a synthesis. **Args:** `[manuscript path]` (default MS). `effort: high`. Tools: Read, Grep, Glob, Write, Bash, Task.
2. **Workflow:**
   - Phase 0: resolve the path; `pdftotext -layout` if PDF; make the output dir.
   - Phase 1: 7 Task calls in one message.
   - Phase 2: `_SYNTHESIS.md` (verdict, cross-lens criticals, scorecard, revision plan, contradictions between lenses).
   - Phase 3: token-budget print (~80–120k).
   - Always exits 0.
   - `--incremental` is labelled "future".
3. **Agents:** lens 1, 2, 4, 5, 7 = `general-purpose`; lens 3 = `domain-reviewer`; lens 6 = `proofreader`. All "context: fork". Lens 7 "invokes `/validate-bib --semantic`" (a skill call from inside a subagent).
4. **Reads:** MS. **Writes:** `QR/seven_pass_[stem]/lens_[N]_[lens-name].md`, `QR/seven_pass_[stem]/_SYNTHESIS.md`.
5. **Cites:** `skills/review-paper`, `skills/validate-bib`, `skills/audit-reproducibility`, "Workflow guide, Pattern 15".
6. **TO-PARAMETERIZE:**
   - Lens 3: "segmentation, 24-zone abstraction, `action##zone` key, heuristic-net discovery".
   - Lens 4: "fitness value", "pitch figures legible with orientation + zone legend".
   - Lens 5: matches/seasons/competitions/providers.
   - Lens 2 econ leftover: "Cochrane / Varian framework".
7. **Missing:** "Workflow guide, Pattern 15" (no guide in the repo); `--incremental`.
8. **Provenance:** none explicit. "Pattern 15" refers to the upstream workflow guide.

### 1.19 `validate-bib`
1. **Description:** Structural bibliography checks; `--semantic` adds drift detection, DOI checks and style. **Args:** `[--semantic] [--skip-doi] [--cite-claim]`. Tools: Read, Grep, Glob, Write, Bash, WebFetch.
2. **Workflow:**
   - Mode 1: bib keys vs `\cite*` keys; missing (CRITICAL), unused, edit-distance ≤2 typos; field quality.
   - Mode 2:
     - 2a drift heuristics (same DOI, same title, same author+year+journal, Jaccard >0.85).
     - 2b DOI/metadata via Crossref, Semantic Scholar and OpenAlex (keyless; max 50 lookups, 0.5s delay, cached).
     - 2c `\cite` style mix.
     - 2d `--cite-claim`: top-10 abstracts, flag only.
   - Exit 1 on any CRITICAL in semantic mode.
3. **Agents:** none.
4. **Reads:** `manuscript/mybib.bib`, MS, `manuscript/*.tex`. **Writes:** `QR/bib_audit_structural.md` or `QR/bib_audit_semantic.md` (the semantic one exists), `QR/.doi_cache.json` (gitignored).
5. **Cites:** `skills/review-paper`, `skills/audit-reproducibility`.
6. **TO-PARAMETERIZE:**
   - `manuscript/mybib.bib`, MS.
   - "LLNCS class with `splncs04.bst` uses `\cite{...}`".
   - `vanderAalst2016` example.
   - Lecture-template leftover: "cited in **lectures**, absent from `.bib`".
   - Doesn't handle biblatex `.bib` resources or multiple bib files.
7. **Missing:** none.
8. **Provenance:** none.

### 1.20 `verify-claims`
1. **Description:** CoVe on any draft via forked `claim-verifier`. **Args:** `[file-or-text-path] [--source <path-or-url>] [--no-fail-closed]`. Tools: Read, Grep, Glob, Task, Write. (No WebSearch/WebFetch; the agent needs its own.)
2. **Workflow:**
   - Phase 0: pre-flight (draft exists, a source exists, agent file exists).
   - Phase 1: claims table (citation, numerical, negative-literature, named entity, dataset).
   - Phase 2: questions.
   - Phase 3: forked verifier.
   - Phase 4: reconcile with v1.9.0 tiers HIGH, MED and LOW-WARN (PASS / PARTIAL / FAIL). Says HIGH "blocks /commit" unless `--no-fail-closed` or `verifyClaims.allowHighWarn`.
3. **Agents:** `claim-verifier` (fork).
4. **Reads:** draft, sources (e.g. `manuscript/mybib.bib`), `.claude/agents/claim-verifier.md`. **Writes:** report (an existing example is `QR/verify_claims_samplepaper.md`; the path pattern isn't specified in the skill).
5. **Cites:** `agents/claim-verifier.md`, `rules/post-flight-verification.md`, MEMORY.md `[LEARN:pattern]`, Dhuliawala et al. 2023 (arXiv:2309.11495).
6. **TO-PARAMETERIZE:** examples: "N = 12,430 possessions", "avg fitness = 0.81", van der Aalst, pm4py, StatsBomb `obv_total_net`, `quality_reports/lit_review_process-mining-sports.md`, Weijters & van der Aalst.
7. **Missing:**
   - `verifyClaims.allowHighWarn` in `settings.json`.
   - The `/commit` gate it describes isn't implemented in `/commit`.
   - The example file `lit_review_process-mining-sports.md` doesn't exist (the real one is `lit_review_process-mining-soccer-2023-2026.md`).
8. **Provenance:** "v1.9.0" tiers label (upstream).

---

## 2. Everything referenced that does NOT exist (confirmed by checking each path)

| Referenced item | Referenced by | Status |
|---|---|---|
| `templates/` (whole dir) | checkpoint, respond-to-referees | MISSING |
| `templates/decision-record.md` | checkpoint (×2) | MISSING |
| `templates/response-to-referees.md` | respond-to-referees (required output structure) | MISSING |
| `master_supporting_docs/`, `.../supporting_papers/` | lit-review, research-ideation, interview-me | MISSING |
| `quality_reports/checkpoints/` | checkpoint | MISSING (would be created on write) |
| `quality_reports/decisions/` | checkpoint, interview-me | MISSING |
| `quality_reports/passports/<slug>.yaml` | audit-reproducibility, `replication-protocol.md` | MISSING |
| `.claude/state/`, `.claude/state/personal-memory.md` | promote-memory (main input), checkpoint | MISSING |
| `check-skill-integrity.py` | deep-audit (acknowledged as not vendored) | MISSING |
| `quality_score.py` or any rubric scorer | implied by commit's 80/90/95 thresholds and `quality-gates.md` | MISSING; scoring is manual |
| `CHANGELOG.md` | checkpoint example | MISSING |
| `README` | deep-audit agents 1 and 4 | MISSING |
| "Workflow guide" (Pattern 15, Cost-Conscious Composition), "landing page" | seven-pass-review, review-paper, deep-audit, model-routing | MISSING |
| `src/results/offensive_statsbomb_pass_09x/` | audit-reproducibility | MISSING (real: `_09`, `_095`, `_099`); `src/results/` is gitignored |
| `quality_reports/lit_review_process-mining-sports.md` | verify-claims example | MISSING |
| `response-to-referees.md` (root), `response-to-referees-matrix.csv` | respond-to-referees outputs | not yet produced |
| `.review-backup/` | review-paper `--adversarial` | not present (runtime) |
| `settings.json` keys `verifyClaims.allowHighWarn`, `--strict-passport` | verify-claims, replication-protocol | MISSING |
| `/learn --revoke` | promote-memory | flag not implemented in `learn` |
| `--incremental` | seven-pass-review | marked future |
| `python_review_*.md` via `/audit-reproducibility` | review-paper output layout | audit-reproducibility doesn't produce it |

Everything else referenced does exist:
- All 9 agents.
- The rules `replication-protocol`, `quality-gates`, `session-logging`, `plan-first-workflow`, `meta-governance`, `python-code-conventions`, `content-invariants` (INV-9..12), `post-flight-verification`, `cross-artifact-review`, `model-routing`.
- The references `journal-profiles` (ML, MLCONF, template), `discipline-cards`, `audit-pet-peeves`.
- The hooks `pre-compact.py` (with `CLAUDE_PRECOMPACT_BLOCK_ON_DRAFT`) and `context-monitor.py` (cache file).
- Manuscript files: Makefile, `llncs.cls`, `splncs04.bst`, `mybib.bib`, figures.
- `review/review1–3.md`, `src/requirements.txt`, `parse_statsbomb_matches.py`, and all `sports_pm` functions and classes.

Note: `verification-protocol.md` exists in `rules/` but **no skill cites it**.

---

## 3. Project-specific coupling: consolidated list of what to parameterize

**Manuscript and build** (compile-latex, proofread, validate-bib, review-paper, seven-pass, devils-advocate, audit-repro, commit, deep-audit):
- `manuscript/` dir, `samplepaper.tex`, `samplepaper.log`, `samplepaper.pdf`, `mybib.bib`, `fig1-5.pdf`.
- `make` / `make clean` / `make cleanall`.
- pdflatex-only ("never xelatex"), bibtex, `splncs04.bst`, `llncs.cls`, "Springer LLNCS".
- `\cite{}`-only convention, Overleaf note, anonymized author block, `xdg-open`.

**Venue:**
- "Springer Machine Learning journal" (review-paper description and Principles), `ML` / `MLCONF` profiles.
- Paper-type default "empirical-ML / computational-pipeline" (interview-me, research-ideation, review-paper).
- `discipline-cards.md` "ml" card.

**Review artifacts:**
- `review/review1–3.md` (devils-advocate).
- R{n}.{m} concern IDs.
- Mixed output conventions: root `response-to-referees.md` vs QR.

**Pipeline** (data-analysis fully; audit-repro, review-paper, seven-pass, deep-audit, learn, commit partly):
- `src/`, run-from-`src/`, `src/results/<run>/`, `src/requirements.txt`, `src/notebooks/discovery/`, `parse_statsbomb_matches.py`.
- `sports_pm` and its functions; pm4py.
- Env vars `TAGS_FILE`, `RESULTS_FILE`, `MONGO_*`; MongoDB snapshot caveat.
- Metric keys `avg_fitness`, `generalization`, `dependency`.
- `python-reviewer` "four documented gotchas".
- Assumes a Python pipeline (json/csv/parquet/pkl readers).

**Domain words:**
- Process mining, heuristic net, conformance or token-replay fitness, dependency threshold.
- Soccer, possession(s), offensive, pitch, 24 zones, `action##zone`, `possession_count`, 105×68, coordinate flip.
- Wyscout/soccerlogs, StatsBomb, `obv_total_net`, tactical.
- van der Aalst, Weijters.
- "previous conference version".

**Upstream leftovers:**
- Econ: FRED/Census/PSID, CPS `educ_attain`, *JEL*, Cochrane/Varian, "non-econ forker", `[LEARN:r-code]`, "descriptive to causal".
- Political science: `v180-polisci` examples.
- Lecture template: "cited in lectures".
- PR #87/#92, issue #25380, version labels v1.7.0, v1.8.0, v1.9.0.

**Hard-coded thresholds** (good candidates for config):
- Tolerances: 0.01 / 0.02 / ±0.1pp / exact.
- Quality gates: 80/90/95.
- Loops: adversarial 5 rounds, deep-audit 5 loops, `--r3` cap, variance N max 5.
- Spend cap ~500k; DOI lookups 50 at 0.5s; match confidence 0.7; checkpoint ~80 lines; MEMORY.md 200 lines.

---

## 4. Provenance summary

| Skill | Attribution |
|---|---|
| checkpoint | Hugo Sant'Anna, clo-author v4.2.0 (github.com/hugosantanna/clo-author), "used with permission", reimplemented |
| review-paper (`--peer` agents) | clo-author (same URL), with permission; AgentReview arXiv:2406.12708 |
| promote-memory | Chris Blattman, claudeblattman v2.1 "Five-critic council" (claudeblattman.com; github.com/chrisblattman/claudeblattman) |
| audit-reproducibility (passport) | Imbad0202/academic-research-skills "Material Passport" (via `replication-protocol.md`) |
| verify-claims, and PFV in lit-review / research-ideation / respond / interview / review-paper | Dhuliawala et al. 2023 CoVe, arXiv:2309.11495 |
| compress-session | Drew Breunig, "How Long Contexts Fail" |
| checkpoint, compress-session, context-status, deep-audit, learn, promote-memory | frontmatter `author: Claude Code Academic Workflow`, `version: 1.0.0` (upstream template name) |

The base template is `pedrohcgs/claude-code-my-workflow` (confirmed by the commit body of `bab1fc2`, see `03_provenance_and_usage.md`). Git history shows the harness arriving in one commit: `bab1fc2 Add academic Claude Code harness (.claude/)`.

---

## 5. Which skills invoke which agents and skills

```
commit ──Task──> verifier, python-reviewer        (claims gates on audit-reproducibility / verify-claims; doesn't implement them)
review-paper ──skill──> audit-reproducibility     (default step 6b and --peer Phase 0; skipped with --no-cross-artifact)
             ──Task──> editor, domain-referee, methods-referee (fork), claim-verifier (fork), general-purpose (re-audit)
seven-pass-review ──skill──> validate-bib --semantic   (lens 7)
                  ──Task──> general-purpose ×5, domain-reviewer, proofreader (fork)
lit-review / research-ideation / interview-me / respond-to-referees / verify-claims ──Task──> claim-verifier (fork)
data-analysis ──Task──> python-reviewer
proofread ──Task──> proofreader
deep-audit ──Task──> general-purpose ×4 (≤5 loops)
promote-memory ──Task──> promote-memory-council ×5 (fork, haiku)
```

Skills that only point at others (no call):
- respond-to-referees → `review-paper --peer --r2`, `seven-pass-review`.
- research-ideation and lit-review → `interview-me`.
- checkpoint and compress-session → `promote-memory`, `context-status`.
- learn ↔ promote-memory.

No agents: compile-latex, devils-advocate, validate-bib, checkpoint, compress-session, context-status, learn. audit-reproducibility allows `Task` but spawns nothing.

---

## 6. The lifecycle these skills imply

| Stage | Skills | Main artifacts |
|---|---|---|
| 1. Ideation | `/research-ideation` | `QR/research_ideation_*.md` |
| 2. Interview / spec | `/interview-me` | `QR/research_spec_*.md`, `QR/decisions/*.md` |
| 3. Literature | `/lit-review`, then `/verify-claims` | `QR/lit_review_*.md`, BibTeX |
| 4. Analysis | `/data-analysis` (project-specific) | `src/…`, `src/results/<run>/` |
| 5. Writing / compile | `/compile-latex`, `/validate-bib`, `/proofread` | PDF, `QR/bib_audit_*.md`, `QR/<file>_report.md` |
| 6. Internal review | `/devils-advocate`, `/review-paper` (default or `--adversarial`), `/seven-pass-review`, `/audit-reproducibility`, `/verify-claims` | `QR/paper_review_*`, `QR/seven_pass_*/`, `QR/reproducibility_*` |
| 7. Simulated peer review | `/review-paper --peer <J>` (`--variance`, `--stress`) | `QR/peer_review_*/` |
| 8. Revise and resubmit | `/review-paper --peer --r2/--r3`, then `/respond-to-referees` | `response-to-referees.md` |
| 9. Commit | `/commit` (quality gate, verifier, PR, merge) | git |
| Throughout: session and memory | `/context-status`, `/checkpoint`, `/compress-session`, `/learn`, `/promote-memory`, `/deep-audit` | `QR/checkpoints/`, `QR/session_logs/`, MEMORY.md, `.claude/skills/` |

For the plugin, these split cleanly:
- **Paper-agnostic core** (needs config for manuscript path, bib, build command, venue profile, paper-type taxonomy, prior-reviews glob): stages 1–3, 5–8, review-paper, seven-pass, validate-bib, verify-claims, respond-to-referees, devils-advocate.
- **Optional "code ↔ paper" add-on** (needs config for outputs dir, metric keys, rerun command, tolerances): audit-reproducibility.
- **Generic session utilities:** checkpoint, compress-session, context-status, learn, promote-memory, deep-audit. These need the hooks and `quality_reports/` scaffolding to ship with them.
- **Project-local, not for the plugin:** data-analysis.
