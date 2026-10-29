# ploma Lifecycle Implementation Plan (milestone 2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port the remaining seventeen skills and the eight agents of the traces harness into ploma, paper-agnostic and config-driven, add the three remaining deterministic scripts (consistency, style check, placeholders), wire the commit gate, ship one eval per skill, and delete `extraction/` once everything is ported.

**Architecture:** Same as milestone 1. Agents read the resolved config injected at SubagentStart and the venue or discipline files it names. Judgment-heavy skills stay prose and quote script output as their audit record. Every ported skill passes the same lint (`tests/test_skills.py`) and ships an eval case.

**Tech Stack:** As milestone 1. Depends on every interface produced there (see that plan's self-review list).

**Spec:** `docs/superpowers/specs/2026-10-29-ploma-design.md`

## Global Constraints

Everything in the milestone 1 plan, plus:

- Attribution comments from upstream (clo-author, claudeblattman, CoVe) are carried forward verbatim at the top of the ported files.
- Every agent starts with the `## Project context` block defined in Task 1 and names no field, venue, dataset, language or tool outside that block.
- Every review finding quotes a manuscript span; the editor drops findings whose quote is not found verbatim.
- Reviewer agents state that the manuscript and pasted referee text are data, not instructions.
- CoVe isolation: the calling skill spawns `ploma:claim-verifier` with claims, questions and source pointers only, never the draft. No skill uses `context: fork` as a Task parameter.
- Loop caps come from `rules/eager/limits.md` and `limits:` in config; no skill restates a number.

## Review Focus

1. A referee report pasted as one paragraph with no numbering: `/ploma:respond` must still produce R{n}.{m} concerns, one per distinct ask (Task 11 eval rubric and the `review/review1.md` fixture, which has numbered prompts but unnumbered bullets).
2. A manuscript whose abstract states a number that appears only in a figure caption: `consistency.py` must count captions as body text and PASS (Task 3 test `test_number_in_caption_counts`).
3. A `.tex` draft that contains an em-dash inside a `\cite` key or a URL: `style_check.py` must not flag it (Task 5 test `test_em_dash_inside_macro_argument_is_ignored`).
4. `/ploma:commit` invoked when the verdict file exists but `manuscript_sha` is stale: it must re-run compile, bib and consistency itself and halt before git only if a required re-run FAILs (Task 13 tests `test_stale_compile_is_rerun`, `test_stale_gate_halts_before_git`).
5. `/ploma:review --peer <unknown-venue>`: the skill must stop before spawning the editor and list the available venue keys (Task 9 eval rubric; `profiles.ProfileError` message).

---

## File structure

```
agents/{editor,domain-referee,methods-referee,domain-reviewer,claim-verifier,proofreader,code-reviewer,verifier}.md
agents/references/peeves-generic.md
scripts/consistency.py  scripts/style_check.py  scripts/placeholders.py  scripts/commit_gate.py
skills/{brainstorm,lit-review,grill,spec,write,format,proofread,verify-claims,audit-reproducibility,review,devils-advocate,respond,commit,checkpoint,compress-session,learn,deep-audit}/SKILL.md
skills/*/references/*.md       long protocols and output templates
templates/project-skills/analysis-pipeline/SKILL.md
schemas/passport.schema.json
evals/<skill>/                 one per skill
tests/test_{consistency,style_check,placeholders,commit_gate,agents}.py
```

---

### Task 1: Agent base block and the eight agents

**Files:**
- Create: `agents/*.md` (eight), `agents/references/peeves-generic.md`, `tests/test_agents.py`
- Modify: `.claude-plugin/plugin.json` (no change needed; `agents/` is auto-discovered; verify with `claude plugin validate .`)

**Interfaces:**
- Produces: the `## Project context` block (identical text in every agent): read the `## ploma project` summary injected at start; when it names a venue profile, read `${CLAUDE_PLUGIN_ROOT}/venues/<key>.yaml` or the `ploma.d/` override named there; when it names a discipline, read the discipline card; when `pipeline.enabled`, read the gotchas and env contract from the summary; if no summary is present, read `ploma.yaml` through `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/ploma_config.py" summary`.
- Agent frontmatter per spec §10 (`model`, `tools`). Names: `editor`, `domain-referee`, `methods-referee`, `domain-reviewer`, `claim-verifier`, `proofreader`, `code-reviewer`, `verifier`.
- `editor.md`: peeve pools become "draw from `agents/references/peeves-generic.md` plus the discipline card's `peeves` plus the venue profile's `peeves`"; the decision table, variance, stress and R&R rules are kept; a "Quote check" step before synthesis drops any referee finding whose quoted span is not found in the manuscript text.
- `methods-referee.md`: paper types come from the discipline card (`paper_types`, `default_paper_type`); the sanity checks per type come from the card.
- `domain-reviewer.md`: persona sentence becomes "a referee for the configured venue in the configured discipline"; the five lenses are kept.
- `code-reviewer.md`: generalised from `python-reviewer.md`; language, run command, env contract and gotchas from the pipeline block; the four soccer gotchas are deleted; category 5 becomes "project gotchas from config".
- `verifier.md`: build through `scripts/compile.py --json`; anonymity check from `document.anonymized`; bib parity through `scripts/bib_check.py`; optional pipeline rerun only when `pipeline.rerun` is set.
- `tests/test_agents.py`: frontmatter `name` equals file stem, `model` in {opus, sonnet, haiku}, `tools` present, body contains `## Project context`, no banned words, no em-dash, attribution comment present for editor, both referees and claim-verifier.

- [ ] **Step 1: Write `tests/test_agents.py`, run it (fails: no agents)**
- [ ] **Step 2: Port the eight agents from `extraction/traces-harness/.claude/agents/`, run the test, run `claude plugin validate .`**
- [ ] **Step 3: Commit** `git commit -m "feat: eight config-driven agents"`

---

### Task 2: Reference protocols shared by skills

**Files:**
- Create: `skills/_shared/references/cove.md` (the four-step CoVe protocol and output block from `post-flight-verification.md`), `skills/_shared/references/finding-format.md`, `skills/_shared/references/report-header.md`

Note: a directory under `skills/` without a `SKILL.md` is not a skill; `tests/test_manifest.py::test_every_skill_dir_has_skill_md` must be changed to skip `_shared`.

- [ ] **Step 1: Update the manifest test, write the three references, run tests, commit** `git commit -m "feat: shared skill references (CoVe, finding format)"`

---

### Task 3: Consistency script

**Files:**
- Create: `scripts/consistency.py`, `schemas/passport.schema.json`, `tests/test_consistency.py`, `tests/fixtures/tex/{consistent,inconsistent,caption_number}.tex`, `tests/fixtures/passport/sample.yaml`

**Interfaces:**
- Produces: `consistency.extract_numbers(text: str) -> list[dict(value: float, raw: str, line: int, kind: count | percent | decimal)]` (ignores years 1900-2099, citation numbers inside `\cite`, labels, `\ref`); `consistency.run(main: Path, *, results_dir: Path | None, metric_keys: list[str], tolerances: dict, passport: Path | None) -> ConsistencyReport` with `findings` (ids `consistency.abstract_number_not_in_body.<raw>` FAIL, `consistency.table_cell_not_in_results.<raw>` WARN when results exist and the cell matches no metric within tolerance, `consistency.passport.<id>` FAIL when a passport claim has status FAIL or STALE), `verdict`, `to_dict()`; body text includes section text, table cells and `\caption{}` content; the abstract is the `abstract` environment or `\abstract{}`. Tolerances: counts exact; decimals within `tolerances.metrics`; percentages within `tolerances.percentages_pp`. CLI: `python3 scripts/consistency.py <main.tex> [--results D] [--metric-keys a,b] [--passport P] [--json]`, exit 1 on FAIL. Records `gate.record("consistency", ...)` when `--root` is given.

- [ ] **Step 1: Write the failing tests**

```python
def test_consistent_fixture_passes(): assert run(FIX / "consistent.tex", results_dir=None, metric_keys=[], tolerances=TOL, passport=None).verdict == "PASS"
def test_abstract_number_missing_from_body(): ids = {f.id for f in run(FIX / "inconsistent.tex", ...).findings}; assert "consistency.abstract_number_not_in_body.550" in ids
def test_number_in_caption_counts(): assert run(FIX / "caption_number.tex", ...).verdict == "PASS"
def test_years_and_cite_numbers_ignored(): assert [n["value"] for n in extract_numbers(r"In 2023 we \cite{a} report 12 teams")] == [12]
def test_table_cell_vs_results(sample_paper): ...   # metrics.json avg_fitness 0.81 vs a table cell 0.85 gives WARN
def test_passport_fail_blocks(): ...
```

- [ ] **Step 2: Run to verify failure, implement, run to verify pass, commit** `git commit -m "feat: deterministic consistency pass"`

---

### Task 4: Audit-reproducibility skill and passport

**Files:**
- Create: `skills/audit-reproducibility/SKILL.md`, `skills/audit-reproducibility/references/passport.md`, `evals/audit-reproducibility/`

Port from traces: phases 0 to 5 with paths, metric keys, rerun command, env contract and tolerances read from the pipeline block; refuse with "pipeline is not enabled in ploma.yaml" otherwise; run `consistency.py` first and quote its output; passport under `<outputs.dir>/passports/<slug>.yaml` created when absent and updated in place (never deletes entries); report `<outputs.dir>/reproducibility_audit_<slug>.md`; `state.record`. Process-mining notes, MongoDB caveat and all examples removed.

- [ ] **Step 1: Port, lint, eval, commit** `git commit -m "feat: audit-reproducibility skill"`

---

### Task 5: Style check and placeholders scripts

**Files:**
- Create: `scripts/style_check.py`, `scripts/placeholders.py`, `tests/test_style_check.py`, `tests/test_placeholders.py`

**Interfaces:**
- `style_check.SLOP_PHRASES: list[str]` (seed: "delve", "leverage", "it is worth noting", "in this paper we", "crucial", "robust framework", "paradigm", "in today's", "a testament to", "landscape"); `style_check.run(text: str, *, forbid_em_dash: bool, extra_phrases: list[str], max_sentence_words: int = 30) -> list[Finding]` with ids `style.em_dash.<line>` (WARN), `style.slop.<phrase>.<line>` (WARN), `style.long_sentence.<line>` (INFO); LaTeX comments, macro arguments (`\cite{}`, `\ref{}`, `\url{}`, `\label{}`, `\includegraphics{}`) and math are stripped before matching. CLI on a file or stdin, `--json`.
- `placeholders.run(files: list[Path]) -> list[Finding]` with ids `placeholder.<kind>.<file>:<line>` for `TODO`, `XXX`, `FIXME`, `\todo{`, `??`, `example.com`, `\today`, `lorem ipsum`; FAIL for all but `\today` (WARN).

- [ ] **Step 1: Tests** including `test_em_dash_inside_macro_argument_is_ignored` and `test_em_dash_in_prose_is_flagged`; `test_placeholders_sample_clean`; `test_placeholders_finds_todo_with_line`.
- [ ] **Step 2: Implement, run, commit** `git commit -m "feat: style check and placeholder scripts"`

---

### Task 6: Write skill

**Files:**
- Create: `skills/write/SKILL.md`, `skills/write/references/sibling-file.md` (header comment format and merge rules), `evals/write/`

Behaviour per spec §7.1. Section resolution: a `\section{...}` title, a `\label{sec:...}`, or a file under `document.root`. Sibling file path `<section-file-dir>/<stem>_suggestion.tex`. Self-check runs `style_check.py` and `consistency.py` on the sibling and lists findings. Shows a unified diff (`diff -u`) and open flags. `--merge` requires the user's yes in the same conversation, applies with Edit, deletes the sibling, recommends `/ploma:compile`. `--from-spec` reads `<outputs.dir>/paper_spec.md` and names the spec items served.

- [ ] **Step 1: Write, lint, eval (rubric: no edit to the manuscript without `--merge`; sibling file created; diff shown; findings listed with line numbers), commit** `git commit -m "feat: write skill with sibling-file drafts"`

---

### Task 7: Format skill

**Files:**
- Create: `skills/format/SKILL.md`, `skills/format/references/cut-plan.md` (the structure of `page_budget_cut_proposal.md`: measured table, principle, cut plan ordered by value per page with page estimates, resulting budget table, what is not cut, risk, recommendation), `skills/format/references/presubmit.md`, `evals/format/`

Behaviour: `/ploma:format [--budget N] [--presubmit]`. Page map from `pdf_pages.section_page_map` with `\section` titles; over budget: draft the cut plan in the reference format, estimating pages per block from the map and figure count; `--presubmit`: run in parallel subagents `chktex -q -n1 -n8 -n36`, `lacheck`, `texcount -inc -sum -brief`, `placeholders.py`, `bib_check.py`, and the venue's `submission_checks` (arXiv rules when the profile lists them), merge by severity into `<outputs.dir>/presubmit_<slug>.md`; tools absent are reported as SKIP with the install hint.

- [ ] **Step 1: Write, lint, eval, commit** `git commit -m "feat: format skill (page budget, cut plan, pre-submission)"`

---

### Task 8: Proofread and verify-claims skills

**Files:**
- Create: `skills/proofread/SKILL.md`, `skills/verify-claims/SKILL.md`, `evals/proofread/`, `evals/verify-claims/`

Proofread: port; one `ploma:proofreader` agent per file; terminology list from `style` and the discipline card; report `<outputs.dir>/<stem>_report.md`; `gate.record("proofread", PASS when no HIGH else WARN, open_high=N)`. Verify-claims: port; spawn `ploma:claim-verifier`; report `<outputs.dir>/verify_claims_<stem>.md` in the sample format; `gate.record("claims", FAIL on any HIGH-WARN else PASS)`; the `verifyClaims.allowHighWarn` setting and the `--no-fail-closed` flag are replaced by the gate override.

- [ ] **Step 1: Port both, lint, evals, commit** `git commit -m "feat: proofread and verify-claims skills"`

---

### Task 9: Review skill (default, adversarial, peer, seven-pass) and devils-advocate

**Files:**
- Create: `skills/review/SKILL.md`, `skills/review/references/{peer-pipeline,adversarial-loop,seven-pass,report-templates}.md`, `skills/devils-advocate/SKILL.md`, `evals/review/`, `evals/devils-advocate/`

Review: `argument-hint: "[path] [--adversarial | --peer <venue> [--r2|--r3|--stress|--variance N] [--no-novelty-check] | --seven-pass] [--no-cross-artifact]"`. The six review dimensions keep their names; the method and evaluation bullets are rewritten generically (the discipline card's sanity checks are cited instead). `--peer` resolves the venue through `profiles.py`; unknown key stops with the available list. Cross-artifact runs `/ploma:audit-reproducibility` only when `pipeline.enabled`. Seven-pass lenses from `seven-pass-review` with domain bullets removed; lens 7 runs `validate_bib.py --semantic` directly instead of a nested skill call. Output paths as spec; `state.record("review", ...)` with the round. Devils-advocate: prior reviews from `reviews.glob`; challenge examples from the discipline card.

- [ ] **Step 1: Port, lint, evals (review rubric: Pre-Flight Report printed; unknown venue lists keys; no edit in default mode), commit** `git commit -m "feat: review and devils-advocate skills"`

---

### Task 10: Brainstorm, lit-review, grill, spec skills

**Files:**
- Create: `skills/brainstorm/SKILL.md`, `skills/lit-review/SKILL.md`, `skills/grill/SKILL.md`, `skills/grill/references/lenses.md`, `skills/spec/SKILL.md`, `skills/spec/references/paper-spec-template.md`, `evals/{brainstorm,lit-review,grill,spec}/`

Brainstorm: when superpowers is enabled (per the injected summary), first invoke `superpowers:brainstorming`, then the ported research-ideation flow; paper types from the discipline card; econ examples removed; CoVe. Lit-review: port; sources from `lit_review.sources` if present in config (add the optional key to the schema: `literature: {sources: [dirs]}`), else the bib files. Grill: one question per turn, the recommended answer stated first with its reason, facts looked up before asking (grep the manuscript, the spec, the bib), lenses rotated per question (theorist, empiricist, pragmatist, reproducibility), terminates when no open decision remains or the user says stop, writes `<outputs.dir>/decisions/<date>_<topic>.md` with every question, the answer and the rationale. Spec: port interview-me into `<outputs.dir>/paper_spec.md` using the template (identity sentence, venue constraints from the profile, claims with evidence pointers, evaluation plan, positioning, section architecture, locked decisions vs open questions, figures needed); when a grill decision log exists, pre-fill locked decisions from it.

- [ ] **Step 1: Port and write, lint, evals (grill rubric: exactly one question per assistant turn, recommended answer present, decision log written), commit** `git commit -m "feat: brainstorm, lit-review, grill, spec skills"`

---

### Task 11: Respond skill

**Files:**
- Create: `skills/respond/SKILL.md`, `skills/respond/references/response-template.md` (header, cover paragraph, per-referee sections with `### R{n}.{m}`, concern matrix), `skills/respond/references/ingestion.md`, `evals/respond/`

Behaviour: `argument-hint: "<report-path-or-dir> [revised-manuscript] [--audit <draft>] [--no-verify]"`. Ingestion: convert pdf, docx, html with `pdftotext`, `pandoc`, `docx2txt` through `mktemp`; reviewer ID from content (`Reviewer #N`, `Reviewer N`, `R{N}`, `Referee N`), never from the file name; when a directory is given, every file matching `reviews.glob`; concerns split by numbered items, bullets, or one per distinct ask inside a paragraph; each concern records id, severity, verbatim quote, summary. Classification and drafting as traces. CoVe on location claims. `--audit` checks an existing draft's coverage and location claims instead of drafting. Output `<outputs.dir>/response_to_referees.md` and `response_to_referees_matrix.csv`; `state.record("respond", ...)`.

- [ ] **Step 1: Port, lint, eval against `examples/sample-paper/review/review1.md` (rubric: concern IDs are `R3.*` because the content says Reviewer #3; every concern classified; warning summary printed), commit** `git commit -m "feat: respond skill with schema-agnostic ingestion"`

---

### Task 12: Session skills: checkpoint, compress-session, learn, deep-audit

**Files:**
- Create: `skills/checkpoint/SKILL.md`, `skills/compress-session/SKILL.md`, `skills/learn/SKILL.md`, `skills/learn/references/ledger-format.md`, `skills/deep-audit/SKILL.md`, `skills/deep-audit/references/checks.md`, `evals/{checkpoint,compress-session,learn,deep-audit}/`
- Modify: `templates/learnings.md` (ledger header matching the format), `templates/rules/ploma-learnings.md` (created-once target for promotion), `scripts/project_files.py` (register the learnings rule as created-once, written only by `/ploma:learn --promote`)

Checkpoint: port; writes `<outputs.dir>/checkpoints/<date>_<slug>.md`; proposed learnings go to the ledger with the user's yes; upstream examples removed. Compress-session: port unchanged except paths. Learn: `argument-hint: "[note | --promote [entry] | --skill <name>]"`; default appends `[LEARN:<topic>] <one line> (<date>)` to the ledger; `--promote` lists ledger entries not yet promoted, proposes the rule text, writes `.claude/rules/ploma-learnings.md` only after approval and marks the entries promoted; `--skill` keeps the old generate-a-project-skill path writing into `.claude/skills/<name>/`. Deep-audit: audits the project's ploma installation: `doctor.py` drift findings, every path mentioned in `.claude/rules/ploma-*.md` and the CLAUDE.md section exists, no project rule restates a `ploma.yaml` fact, cross-document consistency through `consistency.py`, dangling references in `<outputs.dir>/`; four parallel subagents, max five loops, fixes only after approval.

- [ ] **Step 1: Port, lint, evals, commit** `git commit -m "feat: checkpoint, compress-session, learn, deep-audit skills"`

---

### Task 13: Commit gate script and commit skill

**Files:**
- Create: `scripts/commit_gate.py`, `skills/commit/SKILL.md`, `tests/test_commit_gate.py`, `evals/commit/`

**Interfaces:**
- `commit_gate.prepare(root, cfg, *, runner) -> GatePrep` dataclass: runs `gate.check`; when `compile`, `bib` or `consistency` is missing or stale, re-runs `compile.run`, the structural part of `validate_bib.run` (`semantic=False`) and `consistency.run` and records them; halts only when a required check FAILs or the build cannot run; consistency FAIL is a warning in v0.1; returns `verdict`, `stale: list[str]`, `missing: list[str]`, `failing: list[str]`, `warnings`, `can_override`, `override_streak`, `next_commands: list[str]` (the skill commands that refresh each stale or missing recommended check: `/ploma:verify-claims`, `/ploma:proofread`), `to_dict()`. `commit_gate.parse_override(message: str) -> str | None` returns the reason when the user text matches `commit anyway: <reason>` (case-insensitive, reason non-empty). CLI: `python3 scripts/commit_gate.py [--root R] prepare [--json] | override --reason R`.
- `skills/commit/SKILL.md` (`disable-model-invocation: true`, `argument-hint: "[message] [--branch <name>] [--no-pr]"`): Step 0 runs `commit_gate.py prepare`; on INCOMPLETE or FAIL it prints the failing and stale checks with `next_commands` and stops; up to two fix-and-recheck rounds when the user asks; override only on the exact `commit anyway: <reason>` phrase, refused when `can_override` is false, logged through `gate.override` and in the commit body as `ploma-override: <reason>`; Step 0b surface-sync replaced by "run `doctor.py` and stop on NOT_READY"; then the traces git steps with explicit `git add <paths>`, never `-A`; PR creation only with `gh` available and unless `--no-pr`; `state.record("commit", ...)`.

- [ ] **Step 1: Write the failing tests** (`test_stale_compile_is_rerun` asserts that after editing a `.tex` `prepare` calls the compile runner and records a fresh entry; `test_stale_gate_halts_before_git` asserts that when the re-run compile FAILs, `prepare` returns FAIL and the skill's git step is never reached; `test_consistency_fail_only_warns`; `test_consistency_is_run_by_prepare`; `test_parse_override`; `test_override_refused_after_three`)
- [ ] **Step 2: Implement, run, write the skill and eval, commit** `git commit -m "feat: commit skill wired to the gate"`

---

### Task 14: Analysis-pipeline project skill template and onboard hook-up

**Files:**
- Create: `templates/project-skills/analysis-pipeline/SKILL.md`
- Modify: `scripts/project_files.py` (when `pipeline.enabled`, add `.claude/skills/analysis-pipeline/SKILL.md` as created-once, rendered with `pipeline.*` values), `skills/onboard/SKILL.md` (mention the offer), `tests/test_project_files.py`

The template is `data-analysis` with the six-stage soccer chain replaced by `{{ pipeline.stages }}` (optional list key added to the schema), the gotchas and env contract from config, and a Pre-Flight Report that lists the configured values.

- [ ] **Step 1: Test that the file is rendered only when the pipeline is enabled and contains the configured gotchas; implement; commit** `git commit -m "feat: analysis-pipeline project skill template"`

---

### Task 15: Help, README, status catch-up; evals for everything; extraction removal

**Files:**
- Modify: `skills/help/SKILL.md` (all 23 skills listed, no "not yet installed" rows), `README.md` (full lifecycle, every skill, the gate and override rules), `CHANGELOG.md` (`0.1.0`, with the note that consistency becomes a required gate check in 0.1.1), `UPSTREAMS.md` (last-reviewed dates)
- Delete: `extraction/` (one commit, after the check below)

- [ ] **Step 1: Verify nothing shipped references `extraction/`**

Run: `grep -rn "extraction/" --include="*.md" --include="*.py" --include="*.json" --include="*.yaml" . | grep -v "^./extraction/" | grep -v "^./docs/"`
Expected: no output

- [ ] **Step 2: Full suite, validator, evals**

Run: `python3 -m pytest -q && claude plugin validate . && claude plugin eval . --trust-plugin --max-cost-usd 20 --json /tmp/claude-1001/-home-mgarnica-papers/b4e0a978-aa5b-4d23-9754-bdfd063a6d19/scratchpad/evals-m2.json`

> Superseded by R166: no billed eval runs. Run `python3 -m pytest -q && claude plugin validate .` and a headless field test instead.
Expected: tests pass, validate clean, every case passes its `tool_used` grader

- [ ] **Step 3: Tell `traces-16` the port is complete and wait for its confirmation that `extraction/` may go**
- [ ] **Step 4: Delete `extraction/` in one commit**

```bash
git rm -r extraction
git commit -m "chore: remove extraction seed, fully ported"
```

- [ ] **Step 5: Tag the release**

```bash
git tag ploma--v0.1.0 && git push origin main --tags
```

---

## Self-review notes

- Spec coverage: §7 port table rows for every remaining skill (Tasks 4, 6 to 13), §7.1 write (6), §7.2 consistency (3), §10 agents (1), §12 peeves split (1, milestone 1 Task 13), §13 remaining scripts (3, 5, 13), §14 evals (every task), §16 AC6 to AC10 (9, 11, 10, 15, milestone 1 Task 3), AC9 extraction removal (15).
- Interfaces consumed from milestone 1 are used by the names listed in that plan's self-review; new names introduced here: `consistency.run/extract_numbers`, `style_check.run/SLOP_PHRASES`, `placeholders.run`, `commit_gate.prepare/parse_override`.
- Review Focus tests are placed: 1 in Task 11 (eval), 2 in Task 3, 3 in Task 5, 4 in Task 13, 5 in Task 9 (eval).
