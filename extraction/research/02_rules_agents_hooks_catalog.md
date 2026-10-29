# Rules, agents, hooks, settings and references of the traces academic harness (extracted 2026-10-29)

Source repo: `/home/marc/Development/dshs/mlsa/traces` (not readable from r2d2; verbatim copies are in `extraction/traces-harness/`). The harness arrived in two commits: `bab1fc2` "Add academic Claude Code harness (.claude/)" and `4996277` "Enable superpowers plugin in harness settings". It was adapted from pedrohcgs/claude-code-my-workflow, clo-author (Hugo Sant'Anna), Blattman's claudeblattman and Imbad0202's academic-research-skills. Much of the text is still generic template prose. The coupling to this paper is concentrated in about 10 files.

**Inventory corrections first:**
- There are **19** rule files, not 20.
- `templates/`, `scripts/`, `.claude/state/`, `explorations/`, `master_supporting_docs/`, `quality_reports/{specs,merges,passports}/` and a root `MEMORY.md` do **not exist**.
- There is no `.claude/settings.local.json`.

---

## A. Rules (`.claude/rules/*.md`)

Key to the "Scope" field: claude-code `paths:` frontmatter means the rule loads only when matching files are touched. "None" means it loads every session.

### A.1 Rule-by-rule

**1. `content-invariants.md`**
- **Scope:** `manuscript/**/*.tex`, `manuscript/mybib.bib`, `src/**/*.py`, `src/sports_pm/**/*.py`.
- **Purpose:** 12 numbered invariants that reviewers cite by number ("violates INV-3"). INV-1–5 cover the manuscript, INV-6–8 presentation, INV-9–12 the Python pipeline.
  - INV-1 pdflatex only, and `manuscript/` must stay self-contained for Overleaf.
  - INV-2 LLNCS class with `splncs04.bst`.
  - INV-3 authors stay anonymized.
  - INV-4 figures are PDF and `fig1-5.pdf` read standalone; a mirrored pitch is a bug.
  - INV-5 a single `mybib.bib`.
  - INV-6 the contribution fits in one paragraph.
  - INV-7 notation stays consistent.
  - INV-8 honest framing of held-out vs fit-on-train evaluation.
  - INV-9 seeding.
  - INV-10 no hard-coded paths or credentials; use the `MONGO_*`/`TAGS_FILE`/`RESULTS_FILE` env vars.
  - INV-11 the `action##zone` activity key.
  - INV-12 zoning on standardized 105×68 coordinates, with consistent orientation.
- **Numbers:** none beyond 105×68.
- **Referenced by:** `skills/data-analysis`, `rules/post-flight-verification.md` (which calls this file the "Pre-Flight" input side, although it defines no Pre-Flight), `references/audit-pet-peeves.md` #16.
- **Coupling:** very high. INV-2/4/10/11/12 are all specific to this project (LLNCS, soccer pitch, pm4py, MongoDB). INV-1/3/5–9 generalize.

**2. `cross-artifact-review.md`**
- **Scope:** Cursor-style `globs: ["manuscript/**/*.tex","*.tex","src/**/*.py"]` plus `alwaysApply: false`. Claude Code does not recognize `globs:`, so this rule most likely loads every session.
- **Purpose:** when `/review-paper` runs, it auto-invokes the `python-reviewer` agent on each referenced script and `/audit-reproducibility` on the paper/code pair. Results appear as a "Cross-Artifact Findings" section.
- **Behaviour:**
  - Detection is pattern-based: `fig1-5.pdf`, `%% source: src/...` comments, or numeric claims combined with the presence of `src/results/`.
  - Reports go to `quality_reports/cross_artifact_[paper]/`.
  - A reproducibility FAIL escalates to CRITICAL.
  - Opt out with `--no-cross-artifact`.
  - In `--peer` mode this runs as Phase 0, before the desk review. In default and adversarial modes it runs at Step 6b.
- **Coupling:** the dependency graph is hard-coded: `samplepaper.tex` → `src/results/offensive_statsbomb_pass_09x/metrics.json` → `parse_statsbomb_matches.py` → `sports_pm.logic.discovery` → `filters` → MongoDB (`statsbomb_lake`/`staging_soccerlogs`).
- **Referenced by:** `review-paper`, `orchestrator-protocol`, `model-routing`, `post-flight-verification`, pet-peeves #16.

**3. `exploration-fast-track.md`**
- **Scope:** `explorations/**` (the folder does not exist).
- **Purpose:** a lightweight workflow with a 60/100 threshold and no plan. Steps: research-value check → `mkdir explorations/[name]/{R,scripts,output}` → code → log → graduate to 80 or archive. Includes a "kill switch".
- **Leftovers:** mentions "Roxygen docs" and an `R/` folder (from the original R-based template).
- **Referenced by:** `WORKFLOW_QUICK_REF.md`.
- **Coupling:** low.

**4. `exploration-folder-protocol.md`**
- **Scope:** `explorations/**`.
- **Purpose:** all experimental work starts in `explorations/` with an `ACTIVE_PROJECTS.md` and an `ARCHIVE/{completed_,abandoned_}`.
- **Graduation checklist:** quality ≥ 80; manual verification ("no test suite"); results reproduce.
- **Internal inconsistency:** the tree shows `R/`, the lifecycle says `mkdir {src,output}`, and fast-track says `{R,scripts,output}`.
- **Dangling reference:** `templates/archive-readme.md`.
- **Coupling:** graduates into `src/sports_pm/` or `src/notebooks/`.
- **Referenced by:** nobody.

**5. `knowledge-base-template.md`**
- **Scope:** `manuscript/**/*.tex`, `src/**/*.py`.
- **Purpose:** a filled-in project knowledge base with these tables: terminology registry, symbol/field reference, pipeline progression (6 stages), datasets, design principles, anti-patterns, Python pitfalls.
- **Coupling:** 100% project content (possession trace, 24 zones, `possession_count`, `avg_fitness`, Wyscout/StatsBomb, `staging_soccerlogs`/`statsbomb_lake`). Only the table schema is reusable.
- **Referenced by:** nobody by name. `domain-reviewer` says "the knowledge base in `.claude/rules/`".

**6. `meta-governance.md`**
- **Scope:** none (always loaded). 251 lines, the largest rule.
- **Purpose:** declares the repo to be both a working project and a reusable template.
- **Behaviour:**
  - Generic vs specific decision framework.
  - Two-tier memory: a committed `MEMORY.md` capped at 200 lines, plus a gitignored `.claude/state/personal-memory.md`.
  - "Dogfooding" checklist; amendment protocol; a "biology PhD" test for what is generic.
- **Numbers:** MEMORY.md under 200 lines; "nothing ships below 80/100"; a personal 90/100 gate given as an example.
- **Referenced by:** `checkpoint`, `promote-memory`, `promote-memory-council` (the Format critic's schema).
- **Contradictions:**
  - It says MEMORY.md lives at the repo root; the real file is `.claude/MEMORY.md`.
  - It says session logs are committed; `.gitignore` ignores `quality_reports/session_logs/`.
  - It says `.claude/state/` is gitignored; it is **not** listed in `.gitignore`.
  - It references `templates/`, which does not exist.
- **Coupling:** moderate. It uses pm4py, Mongo and `TAGS_FILE` as examples throughout.

**7. `model-routing.md`**
- **Scope:** `.claude/agents/**/*.md`, `.claude/skills/**/SKILL.md`.
- **Purpose:** a 70/20/10 split between Haiku 4.5 (mechanical work), Sonnet 4.6 (`python-reviewer`, `proofreader`) and Opus 4.8 (editor, both referees, claim-verifier, domain-reviewer, verifier).
- **Effort axis:** low/medium for mechanical work, high by default, xhigh for the hardest runs, max rarely.
- **Anti-patterns:** demoting the verifier or editor to a cheaper model; pairing the same model as architect and editor.
- **Other claims:** cost savings of "50–80%"; 5-minute vs 1-hour cache TTL.
- **Contradiction:** every agent except `promote-memory-council` (haiku) is `model: inherit`. The routing table is not applied.
- **Staleness:** the version names are stale (see D.4).
- **Referenced by:** `promote-memory`.
- **Coupling:** none.

**8. `orchestrator-protocol.md`**
- **Scope:** none (always loaded).
- **Purpose:** a 6-step pattern: IMPLEMENT → VERIFY → REVIEW → FIX → RE-VERIFY → SCORE, repeated until the threshold is met. It is explicitly "a pattern, not a runtime".
- **Mapping table:** `/commit` covers steps 2 and 6; `/review-paper --adversarial` 3–5; `/seven-pass-review` 3; `/data-analysis` 1–2; `--peer` 3.
- **Limits:** max 5 review-fix rounds; critic-fixer sub-loop max 5; verification retries max 2.
- **"Just do it" mode:** skips the approval pause but never authorizes a commit.
- **Dangling reference:** `quality_score.py` (the file does not exist).
- **Referenced by:** `plan-first-workflow`.
- **Coupling:** none.

**9. `orchestrator-research.md`**
- **Scope:** `src/**/*.py`, `explorations/**`.
- **Purpose:** a simplified loop (implement → verify → score ≥ 80; "no 5-round loops, no multi-agent").
- **Verification checklist:** run from `src/` with `TAGS_FILE` exported; output node names contain `##`; pitch orientation correct; no silent empty result from Mongo; deps pinned in `src/pyproject.toml` + `uv.lock`.
- **Overlap:** overlaps `orchestrator-protocol` and `verification-protocol`.
- **Referenced by:** nobody.
- **Coupling:** high.

**10. `pdf-processing.md`**
- **Scope:** `master_supporting_docs/**` (the folder does not exist).
- **Purpose:** read PDFs directly with the Read tool, using `pages` (max 20 per request; papers up to about 100 pages). Fall back to Ghostscript splitting into 5-page chunks, then `pdftk`.
- **Coupling:** none. Generic.
- **Referenced by:** nobody (`claim-verifier` mentions `master_supporting_docs/`).

**11. `plan-first-workflow.md`**
- **Scope:** none (always loaded).
- **Purpose:** 9 steps: EnterPlanMode → check MEMORY → requirements spec → plan → save to `quality_reports/plans/YYYY-MM-DD_*.md` → approve → session log → orchestrator.
- **Requirements spec:** used for vague tasks over 1 hour or touching more than 3 files. Ask 3–5 questions; MUST/SHOULD/MAY; CLEAR/ASSUMED/BLOCKED; saved to `quality_reports/specs/` from `templates/requirements-spec.md` (neither the folder nor the template exists).
- **Context survival:** session log updated within the last 10 minutes; "30–50% fewer pivots" claim.
- **Mismatch:** `settings.json` sets `plansDirectory: quality_reports/plans`, and Claude Code names plans randomly (e.g. `soft-cooking-seahorse.md`). That conflicts with the dated naming convention.
- **Referenced by:** `orchestrator-protocol`, `checkpoint`.

**12. `post-flight-verification.md`**
- **Scope:** `paths:` lists 5 SKILL.md files (lit-review, research-ideation, respond-to-referees, review-paper, interview-me), plus `alwaysApply: false`.
- **Purpose:** a 4-step Chain-of-Verification (CoVe) protocol: draft → extract claims → write verification questions → answer them in a forked `claim-verifier`.
- **Outcomes:** PASS / PARTIAL / FAIL. On FAIL, regenerate at most 2 times.
- **Behaviour:** fail-closed if the verifier errors; skip with `--no-verify`; a "Post-Flight Verification" block is required in output.
- **Coupling:** examples cite van der Aalst 2016 and pm4py 2.3.1 (the version is stale; see A.2).
- **Referenced by:** `claim-verifier`, `verify-claims`, the 5 skills above, `model-routing`, pet-peeves #6.

**13. `proofreading-protocol.md`**
- **Scope:** `manuscript/**/*.tex`, `quality_reports/**`.
- **Purpose:** proofreading is mandatory before any commit or PR. Three phases: propose (no edits, report to `quality_reports/`) → user approves → apply.
- **Checks:** grammar, typos, overflow, consistency, academic quality.
- **Coupling:** terms "zone/action/possession/fitness"; `\cite`.
- **Referenced by:** nobody by name (the `proofreader` agent duplicates it).
- **Overlap:** near-duplicate of `agents/proofreader.md`.

**14. `python-code-conventions.md`**
- **Scope:** `src/**/*.py`, `src/sports_pm/**`, `src/notebooks/**`.
- **Purpose:** Python standards for the `sports_pm` pipeline, 10 sections:
  - run from `src/`;
  - reproducibility with uv pins (pm4py 2.7.22.4, pandas 3.0.3, numpy 2.4.6, plotly 5.24.1, kaleido 0.2.1);
  - the env-var contract;
  - the import-time `TAGS_FILE` read;
  - `action##zone`;
  - coordinate flip;
  - PEP8;
  - line length ≤ 100 with a math exception;
  - numerical discipline (no float `==`, explicit NaN policy, stable key dtypes);
  - pitfalls table and checklist.
- **Coupling:** about 90% project-specific.
- **Referenced by:** `python-reviewer`, `data-analysis`, `deep-audit`, `replication-protocol`.
- **Contradiction:** see A.2.

**15. `quality-gates.md`**
- **Scope:** `manuscript/**/*.tex`, `src/**/*.py`.
- **Thresholds:** 80 = commit, 90 = PR, 95 = excellence. They are advisory and enforced only inside `/commit`, which halts below 80 unless the user overrides with a reason that is logged, and warns below 90.
- **Manuscript deductions:** pdflatex failure −100; undefined citation −15; overfull hbox > 10pt −10; typo in an equation or metric −10; notation inconsistency −3; figure lacking orientation/legend −5; minor style −1.
- **Python deductions:** syntax error −100; project-gotcha break −30; hard-coded path or credential −20; unseeded randomness −10; silent Mongo empty result −10; unpinned dependency −5.
- **Tolerance summary:** counts exact; fitness < 0.01; aggregates < 0.02.
- **Reports:** `quality_reports/merges/` (missing).
- **Referenced by:** `orchestrator-protocol`, `orchestrator-research`, `WORKFLOW_QUICK_REF`, `skills/commit`.
- **Coupling:** half the rubric (pitch, Mongo, gotchas) is project-specific.

**16. `replication-protocol.md`**
- **Scope:** `src/**/*.py`, `src/sports_pm/**/*.py`.
- **Purpose:** reproduce before extending, in 4 phases: Inventory/Baseline (`quality_reports/reproduction_targets.md`) → Reproduce (no "improvements", timestamped result directories) → Verify → Extend.
- **Tolerances:**
  - integer counts: exact;
  - fitness/metric point values: < 0.01;
  - generalization/aggregate scores: < 0.02;
  - percentages: < 0.1pp.
- **Also includes:** a MongoDB snapshot caveat; a report template at `quality_reports/reproduction_report.md`.
- **Passport:** `quality_reports/passports/<slug>.yaml`, with schema fields `paper{slug,title,branch,last_audit,last_audit_by}` and `claims[{id,claim,location,source_file,source_line,output_file,output_field,tolerance{point_estimate,n},last_verified_on,last_verified_by,status,notes}]`. Status is PASS, FAIL, STALE or UNVERIFIED.
- **Enforcement:** `/audit-reproducibility`, which exits 1 on any FAIL.
- **Dangling reference:** a `--strict-passport` setting "in `.claude/settings.json`", which does not exist and is not a real Claude Code key.
- **Coupling:** high (example targets fitness 0.81 and 12,430 possessions).
- **Referenced by:** `audit-reproducibility`, `cross-artifact-review`, `single-source-of-truth`, `quality-gates`, `discipline-cards`.

**17. `session-logging.md`**
- **Scope:** none (always loaded).
- **Purpose:** logs at `quality_reports/session_logs/YYYY-MM-DD_*.md`, written at three points: after the plan, incrementally (1–3 lines per decision), and at session end.
- **Templates (missing):** `templates/session-log.md`, `templates/quality-report.md`.
- **Merge reports:** go to `quality_reports/merges/`.
- **Referenced by:** `checkpoint`, `compress-session`, `promote-memory-council`.
- **Coupling:** none.

**18. `single-source-of-truth.md`**
- **Scope:** `manuscript/**/*`, `src/**/*.py`.
- **Purpose:** the source-of-truth chain runs pipeline → `src/results` → manuscript figures and numbers. Never hand-edit a reported number.
- **Results Freshness Protocol:** numbers are read from `metrics.json`, not from memory.
- **Bibliography parity:** every `\cite` key resolves in `mybib.bib`.
- **Coupling:** high (`samplepaper.tex`, `fig1-5.pdf`, `mybib.bib`).
- **Referenced by:** nobody.

**19. `verification-protocol.md`**
- **Scope:** `manuscript/**/*.tex`, `src/**/*.py`.
- **Purpose:** verify at the end of every task.
  - Manuscript: `cd manuscript && make`, `xdg-open` the PDF (Linux-specific), parse the log, confirm anonymization.
  - Pipeline: `uv run python notebooks/discovery/parse_statsbomb_matches.py`; non-empty outputs; fitness within [0,1]; node names contain `##`.
  - Figures: pitch orientation.
- **Referenced by:** nobody. It overlaps the `verifier` agent almost line for line.

### A.2 Contradictions and overlap between rules

**Python toolchain conflict.** Three different toolchain stories coexist:
- `python-code-conventions.md`, `replication-protocol.md` and `orchestrator-research.md` say Python 3.12, uv, pm4py 2.7.22.4, pandas 3.0.3.
- `agents/python-reviewer.md`, `agents/domain-reviewer.md`, `references/discipline-cards.md`, `WORKFLOW_QUICK_REF.md` and the post-flight examples say Python 3.9, `src/requirements.txt`, pm4py 2.3.1, pandas 1.5.2. `methods-referee` cites `src/requirements.txt`.
- The actual `src/pyproject.toml` has `requires-python >=3.12`, `pm4py>=2.7.11`, `pandas>=2.2`.

**Tolerances.** The `quality-gates` summary omits the percentage row (< 0.1pp) that `replication-protocol` defines.

**Quality thresholds stated in different places:**
- 80/90/95 in `quality-gates`;
- 60 for explorations in fast-track;
- ≥ 80 in `orchestrator-research` and the graduation checklist;
- "No Exceptions ≥ 80" in `WORKFLOW_QUICK_REF`, versus "user may override" in `quality-gates`;
- a personal 90 shown as an example in `meta-governance`.

**Round limits.** `orchestrator-protocol` sets 5 main / 5 critic-fixer / 2 verification retries. `post-flight` allows 2 regenerations. `orchestrator-research` says "no 5-round loops". These are consistent but scattered.

**Duplicated verification checklists.** `verification-protocol`, `orchestrator-research`, `agents/verifier.md`, the gotchas section of `python-code-conventions`, and `content-invariants` INV-9–12 all restate the same four gotchas (`TAGS_FILE`, `##`, coordinate flip, env contract).

**Proofreading duplicated.** `proofreading-protocol` and `agents/proofreader.md`.

**Model routing not applied.** `model-routing` prescribes tiers, but agents are `inherit`.

**Exploration folder layout.** Three different skeletons across `exploration-fast-track` and `exploration-folder-protocol`, with R-language leftovers.

**Memory and git layout.** `meta-governance` disagrees with `.gitignore` and the actual layout (MEMORY.md location, session logs committed, `.claude/state/` gitignored).

**Scoping syntax.** `cross-artifact-review` uses Cursor's `globs:`/`alwaysApply` instead of `paths:`. `post-flight-verification` mixes `paths:` with `alwaysApply`.

**Always-loaded rules (no `paths:`):** `meta-governance`, `orchestrator-protocol`, `plan-first-workflow`, `session-logging`, and effectively `cross-artifact-review`.

**Rules scoped to folders that don't exist:** `pdf-processing` and both exploration rules.

**Dangling references.** 7 templates (`requirements-spec`, `session-log`, `quality-report`, `archive-readme`, `journal-profile-template`, `decision-record`, `response-to-referees`); `scripts/check-skill-integrity.py` and `scripts/check-model-versions.sh`; `quality_score.py`; the `--strict-passport` and `verifyClaims.allowHighWarn` "settings".

---

## B. Agents (`.claude/agents/*.md`)

### B.1 Exact frontmatter

```yaml
---
name: claim-verifier
description: Fresh-context verifier for factual claims made by other agents or skills. Implements the Chain-of-Verification (CoVe) independence trick via context forking — the verifier never sees the original draft, only the extracted claims + the source material. Use when a skill has produced a draft that contains citations, numerical facts, named entities, or literature references that need hallucination-checking before returning to the user.
tools: Read, Grep, Glob, WebFetch, WebSearch, Bash
model: inherit
---
```
```yaml
---
name: domain-referee
description: Substantive referee for a manuscript. Reviews contribution, literature positioning, substantive argument, external validity, and journal fit. Calibrated to a target journal and primed with a disposition + pet peeves by the editor agent. Used by `/review-paper --peer`.
tools: Read, Grep, Glob
model: inherit
---
```
```yaml
---
name: domain-reviewer
description: Substantive domain review for the manuscript (process mining / sports analytics / applied ML). NOT disposition-primed. Checks method soundness, derivation/metric correctness, citation fidelity, code-theory (pipeline) alignment, and logical consistency. Use after content is drafted or before submission.
tools: Read, Grep, Glob
model: inherit
---
```
```yaml
---
name: editor
description: Journal editor who desk-reviews manuscripts, selects two referees with deliberately different dispositions, calibrates to a target journal from `.claude/references/journal-profiles.md`, and synthesizes an editorial decision (FATAL / ADDRESSABLE / TASTE). Used by `/review-paper --peer [journal]`.
tools: Read, Grep, Glob, WebSearch, WebFetch
model: inherit
---
```
```yaml
---
name: methods-referee
description: Methodology referee for a manuscript. Paper-type-aware (empirical-ML / computational-pipeline being the default for this repo, plus reduced-form / structural / theory+empirics / descriptive / formal-theory / survey-experiment), each with its own dimension weights and mandatory sanity checks. Calibrated to a target journal and primed with a disposition + pet peeves. Used by `/review-paper --peer`.
tools: Read, Grep, Glob
model: inherit
---
```
```yaml
---
name: promote-memory-council
description: Five-critic council that votes YES/NO on whether candidate `[LEARN]` entries should be promoted from `.claude/state/personal-memory.md` (gitignored) to MEMORY.md (committed). Each critic reviews one dimension — generality, staleness, redundancy, evidence, format — in an isolated forked context. Invoked by `/promote-memory`.
tools: Read, Grep, Glob
model: haiku
---
```
```yaml
---
name: proofreader
description: Expert proofreading agent for the academic manuscript. Reviews for grammar, typos, overflow, and consistency. Use proactively after creating or modifying manuscript content.
tools: Read, Grep, Glob
model: inherit
---
```
```yaml
---
name: python-reviewer
description: Python code reviewer for the process-mining pipeline (Python 3.9, pm4py / pandas / plotly / floodlight / pymongo). Checks code quality, PEP8, pandas / pm4py idioms, reproducibility, and the four documented project gotchas. Use after writing or modifying Python scripts/modules under `src/`.
tools: Read, Grep, Glob
model: inherit
---
```
```yaml
---
name: verifier
description: End-to-end verification agent. Checks that the manuscript compiles and the Python pipeline runs and produces valid outputs. Use proactively before committing or creating PRs.
tools: Read, Grep, Glob, Bash
model: inherit
---
```

### B.2 Role, inputs/outputs, callers, coupling

**`editor`** (367 lines; credited to clo-author)
- **Role:** desk review → referee selection → synthesis. Explicitly "not a third referee".
- **Inputs:** manuscript path; `--peer <JOURNAL>`; flags `--no-novelty-check`, `--stress`, `--variance N` (N = 3–5), `--r2`/`--r3`.
- **Phase 1 (desk review):**
  - Reads `journal-profiles.md`. If the profile is missing, it stops and points to `templates/journal-profile-template.md` (which doesn't exist).
  - Runs up to 3 WebSearch novelty probes.
  - Six desk-reject criteria, including a reproducibility FAIL from Phase 0.
  - Output: `quality_reports/peer_review_[paper]/desk_review.md`.
- **Phase 3 (synthesis):**
  - Classifies each concern as FATAL, ADDRESSABLE or TASTE.
  - Decision table: 0 FATAL with 0–3 ADDRESSABLE → Minor; 0 FATAL with 4+ → Major; 1 addressable FATAL → Major; any unaddressable FATAL or 2+ FATAL → Reject.
  - Output: `editorial_decision.md`.
- **Variance mode:** writes `decision_distribution.md` and `editor_synthesis.md`.
- **R&R mode:** reuses the prior round's dispositions and peeves; `--r3` cannot return Major.
- **Stress mode:** both referees forced to SKEPTIC, with 2 critical peeves each.
- **Called by:** `/review-paper --peer` (also mentioned in `respond-to-referees` and `CLAUDE.md`).
- **Coupling:**
  - The 29 critical and 25 constructive peeve pools are hard-coded in the agent body, about 15 of them soccer/pm4py-specific (zone granularity, `filter_offensive_sequences`, the `y -> FIELD_WIDTH - y` flip, Wyscout vs StatsBomb, "fitness 0.8 tactically").
  - The variance example also uses fitness.
  - The structure is generic.

**How dispositions and pet peeves are injected (editor → referees).** Injection is file-mediated, not prompt-parameterized:
1. The editor's Phase 1b draws disposition D1 from the journal's `Referee-pool weights`, removes D1, renormalizes the remaining weights, and draws D2. Each referee also gets 1 critical and 1 constructive peeve, drawn uniformly from the flat pools in `editor.md`.
2. The editor writes a "Referee Selection" table into `desk_review.md` (Referee A = domain, Referee B = methods).
3. `/review-paper` spawns `domain-referee` and `methods-referee` in parallel as forked subagents, "with disposition D1, peeves P1".
4. Each referee is told to read its disposition and peeves from `desk_review.md` and print `Calibrated to: …, Disposition: …`. At least one major concern must map to the critical peeve.

Further details:
- **Dispositions (6):** METHODOLOGY/RIGOR, REPRODUCIBILITY, NOVELTY/RELATED-WORK, EVALUATION/VALIDITY, CLARITY/PRESENTATION, SKEPTIC.
- **Variance mode:** draws with replacement and inserts a SKEPTIC if none was drawn.
- **Flag conflicts:** `--variance` is incompatible with `--stress` and `--r2`.
- **Gap:** the variance-mode referee files are named `referee_1..N.md`, but the referee agents only document `referee_domain.md`/`referee_methods.md`. It is unclear which agent type plays referees 3–5.

**`domain-referee`** (137 lines)
- **Role:** "is this a contribution?"
- **Dimension weights:** Contribution 30, Literature 25, Substantive arguments 20, External validity 15, Fit 10. These are re-weighted by the journal profile.
- **Score bands:** 90+ accept, 80–89 minor, 65–79 major, < 65 reject.
- **Requirements:** "What would change my mind" on every MAJOR concern; at most about 2500 words.
- **R&R:** each prior concern classified as Resolved, Partial or Not addressed; output gets `_r2`/`_r3` suffixes.
- **Output:** `referee_domain.md`.
- **Coupling:** the disposition guidance text mentions possession segmentation, the 24-zone grid, `action##zone`, MongoDB, and "process-mining-for-sports".

**`methods-referee`** (245 lines)
- **Role:** identifies the paper type first. Seven types: empirical-ML/computational-pipeline (the repo default) plus six econ/poli-sci types inherited from clo-author.
- **Per-type weights:** ML type is Method 25, Evaluation validity 30, Baselines/ablations 20, Generalization 15, Reproducibility 10.
- **Sanity checks:** mandatory blocker checks per type; any FAIL caps the score at 70. The ML checks are held-out evaluation, leakage, baseline, hyperparameter honesty (the dependency sweep from 0 to 0.99), reproducibility (`src/requirements.txt`, `TAGS_FILE`/`MONGO_*`) and determinism.
- **10 rules,** including treating an `/audit-reproducibility` FAIL as FATAL.
- **Output:** `referee_methods.md`.
- **Coupling:** the ML-type text is soccer/pm4py-specific. The econ/poli-sci types are generic ballast.
- **Other references:** mentioned by `research-ideation`, `interview-me` and `checkpoint` as the source of the paper-type taxonomy.

**`domain-reviewer`** (152 lines)
- **Role:** not disposition-primed. The persona is "Springer Machine Learning journal referee … process mining and sports analytics".
- **5 lenses:** method assumptions, metric/derivation, citation fidelity (`mybib.bib`, `review/review1–3.md`), pipeline–paper alignment (`src/sports_pm/`), backward logic. Plus a cross-section consistency check.
- **Output:** `quality_reports/[file]_substance_review.md`.
- **Called by:** `/seven-pass-review`; also mentioned in `respond-to-referees` and `audit-reproducibility`.
- **Coupling:** very high. It cites pm4py 2.3.1 (stale).

**`claim-verifier`** (123 lines)
- **Role:** CoVe verifier. It must never see the draft; it is meant to run via `Task` with `context: fork`.
- **Input:** a YAML block of `source_material` and `claims` (each with `id`, `text`, `source_hint`, `verification_question`).
- **Output:** a per-claim table with `matches_claim` (yes, partial, no, cannot-verify, not-verifiable-claim-type).
- **Severity tiers:** HIGH-WARN (fabricated reference, numerical or directional contradiction; blocks `/commit`), MED-WARN (transient failure), LOW-WARN (source inaccessible).
- **Constraint:** WebSearch alone is never enough evidence.
- **Called by:** `verify-claims`, `lit-review`, `research-ideation`, `respond-to-referees`, `review-paper` (`--peer` novelty), `interview-me`.
- **Coupling:** only the examples (van der Aalst, pm4py 2.3.1, 12,430 possessions).

**`python-reviewer`** (181 lines)
- **Persona:** "Senior Principal Data Engineer + PhD".
- **11 categories;** category 5 covers the four project gotchas (a) `TAGS_FILE` at import, (b) `action##zone`, (c) coordinate flip, (d) env contract, with violations rated at least High.
- **Domain-correctness category:** segmentation rules, the offensive filter, the 24-zone grid, token-replay fitness, `get_match_info`.
- **Output:** `quality_reports/[script]_python_review.md`, or `cross_artifact_*/python_review_*.md` when called from cross-artifact review.
- **Called by:** `cross-artifact-review` (via `/review-paper`), `/commit`, `/audit-reproducibility`, `/deep-audit`, `/data-analysis`.
- **Coupling:** about 70% project-specific. The toolchain is stale (Python 3.9, pm4py 2.3.1, pandas 1.5.2, `requirements.txt`), contradicting the conventions rule.

**`verifier`** (78 lines)
- **Role:** the only agent with Bash. Runs `cd manuscript && make`; parses `samplepaper.log` for overfull boxes, undefined citations and changed labels; checks anonymization.
- **Pipeline check:** runs `cd src && python notebooks/discovery/parse_statsbomb_matches.py` (plain `python`, not `uv run`). Checks outputs, fitness in [0,1], `##` in node names, and treats an empty Mongo result as a HARD FAIL. Also checks figures and bibliography keys.
- **Called by:** `/commit`, as `Task subagent_type=verifier`.
- **Coupling:** very high.

**`proofreader`** (62 lines)
- **Role:** checks 5 categories and writes a report with Current/Proposed/Category/Severity to `quality_reports/[file]_report.md`. Never edits.
- **Called by:** `/proofread`, `/seven-pass-review`.
- **Coupling:** low (`samplepaper.tex`, `splncs04.bst`, terminology list).

**`promote-memory-council`** (104 lines)
- **Model:** `haiku` (the only routed agent).
- **Role:** one of 5 isolated critics (Generality, Staleness, Redundancy, Evidence, Format). Output is exactly `**Vote:** YES|NO` plus a one-line rationale.
- **Called by:** `/promote-memory`.
- **Coupling:** none to this project. It does contain upstream residue: "non-econ forker", `/Users/pedrosantanna/Dropbox/...`, `$\hat{\beta}$`.

---

## C. Hooks, statusline and `settings.json`

### C.1 Full `settings.json` (both blocks verbatim)

`permissions` and the trailing keys:
```json
"permissions": {
  "allow": [
    "Bash(make:*)", "Bash(pdflatex:*)", "Bash(bibtex:*)", "Bash(latexmk:*)", "Bash(pdftotext:*)",
    "Bash(python:*)", "Bash(python3:*)", "Bash(pip:*)",
    "Bash(git status:*)", "Bash(git diff:*)", "Bash(git log:*)", "Bash(git show:*)", "Bash(git add:*)", "Bash(git branch:*)",
    "Bash(ls:*)", "Bash(cat:*)", "Bash(head:*)", "Bash(tail:*)", "Bash(grep:*)", "Bash(rg:*)", "Bash(find:*)", "Bash(wc:*)",
    "WebFetch", "WebSearch"
  ],
  "deny": [
    "Read(**/.env)", "Read(**/.env.*)", "Write(**/.env)", "Write(**/.env.*)", "Edit(**/.env)", "Edit(**/.env.*)"
  ],
  "defaultMode": "default"
},
"statusLine": { "type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR\"/.claude/scripts/statusline.sh" },
"plansDirectory": "quality_reports/plans",
"enabledPlugins": { "superpowers@superpowers-marketplace": true }
```

`hooks` block (verbatim):
```json
"hooks": {
  "Notification": [
    { "hooks": [ { "type": "command", "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/notify.sh", "timeout": 5 } ] }
  ],
  "PreCompact": [
    { "hooks": [ { "type": "command", "command": "python3 \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/pre-compact.py", "timeout": 10 } ] }
  ],
  "SessionStart": [
    { "matcher": "compact|resume",
      "hooks": [ { "type": "command", "command": "python3 \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/post-compact-restore.py", "timeout": 5 } ] }
  ],
  "PostToolUse": [
    { "matcher": "Bash|Task",
      "hooks": [ { "type": "command", "command": "python3 \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/context-monitor.py", "timeout": 5 } ] },
    { "matcher": "Write|Edit",
      "hooks": [ { "type": "command", "command": "python3 \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/verify-reminder.py", "timeout": 5 } ] }
  ],
  "Stop": [
    { "hooks": [ { "type": "command", "command": "python3 \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/log-reminder.py", "timeout": 10 } ] }
  ]
}
```

**Permission observations:**
- `pip:*` is allowed but `uv` is not, although the project is uv-managed.
- `python:*`/`python3:*` are allowed with no restriction.
- `git add` is allowed; `git commit`/`push` are not, so `/commit` will prompt.
- `latexmk` is allowed although the rules say make/pdflatex.
- There are no `Edit`/`Write` allow rules.
- No `bypassPermissions` (matching the claim in `CLAUDE.md`).

### C.2 Where hook state lives (shared by all hooks)

Every Python hook writes to `~/.claude/sessions/<md5(CLAUDE_PROJECT_DIR)[:8]>/` in the **user's home directory**, not to `.claude/state/` and not to the project. `~/.claude/sessions/70af9703` and `c51a295b` exist on this machine. The `.gitignore` entry `.claude/sessions/` (project-relative) therefore matches nothing these hooks write. Every hook fails open (`except Exception: exit 0`).

### C.3 Hook by hook

**`notify.sh`** (Notification event)
- Reads `.message`/`.title` with **jq** and exits 0 silently if jq is missing.
- Notifies via `osascript` on macOS, `notify-send` on Linux, or stderr otherwise.
- No state. No project coupling.

**`pre-compact.py`** (PreCompact event)
- Scans the 3 newest `quality_reports/plans/*.md`, skipping any containing the substring "COMPLETED". Status is decided by substring search for APPROVED/DRAFT, which is fragile: a plan that merely mentions "approved" counts as approved. The current task is the first `- [ ]` line.
- Scans the last 50 lines of the newest session log for markers (`Decision:`, `Decided:`, `Chose:`, `→`, `•`) and keeps up to 3.
- Writes `pre-compact-state.json`.
- Appends a "Context compaction" note to the newest session log. This modifies a project file.
- Prints an ANSI-colored summary to stderr.
- Optionally blocks compaction once per DRAFT plan when `CLAUDE_PRECOMPACT_BLOCK_ON_DRAFT=1`, using `precompact-block-sentinel.json`.

**`post-compact-restore.py`** (SessionStart, matcher `compact|resume`)
- Reads and deletes `pre-compact-state.json`.
- Reports the newest plan's status and task and the newest session log name.
- Emits JSON `hookSpecificOutput.additionalContext` with recovery steps.

**`context-monitor.py`** (PostToolUse on `Bash|Task`)
- Estimates context as transcript bytes / 4 against `CLAUDE_CONTEXT_WINDOW_TOKENS` (default 1,000,000). The fallback is a tool-call counter against `CLAUDE_CONTEXT_MAX_TOOL_CALLS` (default 400).
- Nudges at 40, 55 and 65% to suggest `/learn`; info note at 80%; caution at 90%.
- Throttled to once per 60 s below 80%.
- State: `context-monitor-cache.json`.
- Output: `systemMessage` plus `additionalContext`.
- Its text references `/learn` and Opus 4.8 / Sonnet 4.6.

**`verify-reminder.py`** (PostToolUse on `Write|Edit`)
- `VERIFY_EXTENSIONS` covers `.tex` ("compile with /compile-latex"), `.qmd` and `.R`.
- **Bug:** the suffix is lower-cased before lookup, so `.R` never matches.
- **No `.py` entry,** so edits to the Python pipeline trigger no reminder.
- Skips docs, config and `.bib`/`.cls`/`.sty` files, and the `/docs/`, `/templates/`, `/quality_reports/`, `/.claude/` directories.
- Deduplicates per file for 300 s via `verify-reminder-cache.json`.

**`log-reminder.py`** (Stop event)
- Never blocks.
- Writes to stderr once if `quality_reports/session_logs/` has no log.
- Otherwise writes to stderr once after `THRESHOLD = 50` responses without the newest log's mtime changing.
- Respects `stop_hook_active`. Uses `cwd` from stdin.
- State: `log-reminder-state.json`.

**`scripts/statusline.sh`**
- Reads stdin JSON via **python3** (one fork).
- Shows `[BYPASS]`, `[AUTO-EDIT]`, `[PLAN]` or `[PROMPT]`, the model display name, and `@ branch` from `git -C cwd branch --show-current`.
- No state. No coupling.

### C.4 External dependencies and portability

- **Dependencies:** python3 (5 hooks plus the statusline), jq (notify only), notify-send or osascript, git, bash.
- **Machine-specific values:** none hard-coded (no absolute paths). Everything is keyed off `$CLAUDE_PROJECT_DIR`.
- **Project assumptions baked in:** the `quality_reports/plans` and `quality_reports/session_logs` layout and the plan status vocabulary (DRAFT/APPROVED/COMPLETED).
- **Leftovers:** the `.qmd`/`.R` extensions in verify-reminder come from the upstream template.

---

## D. References, MEMORY and the quick reference

### D.1 `references/journal-profiles.md` (179 lines; credited to clo-author)

**Schema, per journal:**
- Short name (the `--peer` argument)
- Focus
- Bar
- Domain-referee adjustments (dimension X → Y)
- Methods-referee adjustments
- Typical concerns (3–5 quoted questions)
- Referee-pool weights over the 6 dispositions (must sum to 1.0)
- Table format override (optional)

**`ML` (Springer *Machine Learning*):**
- Domain adjustments: Contribution 30→35, Literature 25→30, Fit 10→5.
- Methods adjustments: Evaluation 30→35, Reproducibility 10→15, Baselines unchanged at 20.
- Weights: EVAL 0.25, METH 0.20, REPRO 0.20, NOVELTY 0.15, SKEPTIC 0.10, CLARITY 0.10.
- 6 concerns, soccer-specific (zones, `action##zone`, Wyscout vs StatsBomb, "what transfers beyond soccer").
- Table override: no stars; give N matches/possessions; pitch orientation and legend.

**`MLCONF` (a stand-in for the previous conference round, `review/review1–3.md`):**
- Domain adjustments: Contribution 30→35, External validity 15→10.
- Methods adjustments: Baselines 20→25, Reproducibility 10→5.
- Weights: NOVELTY 0.30, EVAL 0.20, CLARITY 0.20, METH 0.15, SKEPTIC 0.10, REPRO 0.05.

**Also included:** a field-adaptation template and unfilled stubs for JMLR, DAMI, NeurIPS/ICML.

**Consumers:** `editor`, both referees, `review-paper`.

### D.2 `references/discipline-cards.md` (86 lines)

**One card only: `ml`** (applied ML / data mining, process mining for sports).
- Paper-type shares: empirical-ML pipeline about 60%, methods/algorithm about 20%, benchmark about 10%, application about 10%.
- Venues: `ML`, `MLCONF`.
- Reproducibility norms: code release, held-out evaluation, baselines, plus a MongoDB caveat.
- Method conventions: no significance stars; seeds; Python 3.9 + pm4py/floodlight/pymongo (stale); readable pitch figures.

**Also included:** a card template and a 4-step guide for adding a discipline.

**Consumers:** `research-ideation`, `interview-me`, `editor`.

### D.3 `references/prompt-formatting-core.md` (178 lines; from Blattman)

**Essence:**
- A six-part prompt skeleton: Role → Task (verb-first) → Context (5–8 bullets) → Constraints (prefer MUST NOT) → Output format → Bookend ("ask one clarifying question if ambiguous").
- Depth calibration:
  - Light: under 40 words; Role, Task, Format and Bookend only.
  - Standard: 40–200 words or domain jargon; all six parts plus an Assumptions block.
  - Deep: over 200 words, a specific paper, or "for submission"; adds an Investigation pre-step.
  - A `depth:` override is honored.

**Also included:** a worked example (responding to a referee's fit-on-train fitness concern; soccer-flavoured); a "What we don't ship" section (multi-vendor routing, a `council` token); the boundary with `/interview-me`.

**Coupling:** examples only.

### D.4 `references/model-versions.md` (33 lines). Stale.

**Contents:**
- Marker `<!-- CURRENT: Opus 4.8 | Sonnet 4.6 | Haiku 4.5 -->`, "Last verified 2026-05-31".
- Table: `claude-opus-4-8` (GA 2026-05-28, $5/$25, 1M context, high effort), `claude-sonnet-4-6` (1M), `claude-haiku-4-5-20251001`.
- Retiring 2026-06-15: Sonnet 4 and original Opus 4.
- Fast-mode pricing; Opus 4.7 listed as the prior generation.
- An update protocol that relies on `scripts/check-model-versions.sh` and `CHANGELOG.md`, neither of which exists.

**Why it's stale:** it is five months old as of 2026-10-29; current models are the Claude 5 family (Fable 5.1, Opus 5.5, Sonnet 5.5, Haiku 5.5). The same stale names appear in `model-routing.md` and `context-monitor.py`.

### D.5 `references/audit-pet-peeves.md` (252 lines)

**What it is:** a living catalogue of 19 harness-maintenance bug classes that review bots caught and deep-audit missed. Read by `/deep-audit`.

**The 19 classes:**
1. Missing `Task` in `allowed-tools`.
2. `argument-hint` ↔ flag parity.
3. Broken anchors.
4. Unimplemented flags.
5. Stale docstrings.
6. Rule ↔ skill parity.
7. Enumerative-summary drift.
8. Count-shorthand ordering.
9. Agent ↔ skill scope contradictions.
10. "Daemon" phrasing.
11. Stale prose counts.
12. Don't edit historical CHANGELOG entries.
13. Docstring contract drift.
14. Narrow `except` breaking fail-open.
15. `set -u` vs `set -e`.
16. Dead config-map entries.
17. CronCreate vs Routines.
18. Enumerative-table drift.
19. Generalized tool-name parity.

**Coupling:** none to this project. It refers to the upstream repo's PRs (#87–#93), `scripts/check-skill-integrity.py` (missing here), and CHANGELOG versions v1.6–v1.9.

### D.6 `.claude/MEMORY.md`

The file holds a header and an empty learnings section. **There are zero `[LEARN:...]` entries.** The full file:

```
# Project Memory

Project-specific learnings index. The `/learn` and `/promote-memory` skills append entries here (tagged `[LEARN:<topic>]`); keep it under ~200 lines so it stays loadable. Machine/personal learnings go in `.claude/state/personal-memory.md` (gitignored), not here.

## Learnings

<!-- Append [LEARN:<topic>] one-liners below, newest at the bottom. -->
```

`claim-verifier` and `verify-claims` both cite "MEMORY.md `[LEARN:pattern]` on CoVe vs critic-fixer". That entry does not exist.

### D.7 `.claude/WORKFLOW_QUICK_REF.md` (92 lines)

**Contents:**
- The "Contractor" loop (plan → execute → report).
- When Claude asks vs when it just executes.
- Quality gate "≥ 80, no exceptions".
- Seven project non-negotiables: run from `src/`; `TAGS_FILE`; `action##zone`; pitch orientation; `make` with pdflatex; anonymization; pins in `src/requirements.txt` (pm4py 2.3.1, pandas 1.5.2, stale versus uv); env-var contract.
- An unfilled Preferences section.
- Exploration mode at 60/100.

**Coupling:** high.

---

## E. `.gitignore` and directory existence

**Harness-relevant `.gitignore` entries:**
- `.claude/settings.local.json`
- `.claude/**/*.local.*`
- `.claude/sessions/` (matches nothing; hooks write to `~/.claude/sessions/`)
- `quality_reports/session_logs/` (contradicts `meta-governance`, which says logs are committed)
- `quality_reports/.doi_cache.json`
- `**/.env`, `**/.env.*`, `!**/.env.example`
- `src/results/`, `src/notebooks/results/` (relevant because the audit/passport `output_file` paths would then be untracked)
- Manuscript build artifacts, including `samplepaper.pdf`

**Missing from `.gitignore`:** `.claude/state/`, although `meta-governance`, `promote-memory` and the council all describe `personal-memory.md` as gitignored.

**Existence check:**

| Path | Exists? |
|---|---|
| `templates/` | No (7 templates referenced) |
| `.claude/state/` | No |
| `quality_reports/specs/` | No |
| `quality_reports/merges/` | No |
| `quality_reports/passports/` | No |
| `quality_reports/plans/` | Yes (4 randomly named plans) |
| `quality_reports/session_logs/` | Yes (`2026-06-04_rr-revision-kickoff.md`, gitignored) |
| other `quality_reports/` files | Yes: `bib_audit_semantic.md`, `lit_review_…md`, `page_budget_cut_proposal.md`, `paper_review_samplepaper_round1.md`, `response_to_referees_draft.md`, `samplepaper_report.md`, `verify_claims_samplepaper.md` |
| `scripts/` (repo root) | No |
| `explorations/` | No |
| `master_supporting_docs/` | No |
| `review/` | Yes |
| root `MEMORY.md` | No (lives at `.claude/MEMORY.md`) |
| `.claude/settings.local.json` | No |

---

## Implications for a paper-agnostic plugin

**Already generic** (lift almost unchanged):
- `orchestrator-protocol`, `plan-first-workflow`, `session-logging`, `pdf-processing`, `model-routing` (once versions are refreshed), `meta-governance` (once the layout contradictions are fixed).
- `post-flight-verification`; `claim-verifier`; `promote-memory-council`.
- The editor/referee machinery and the disposition taxonomy.
- `prompt-formatting-core`; all hooks; the statusline.

**Project-specific content to move into per-project config files:**
- The pipeline gotchas, which today are spread across 8 files.
- Env vars and paths: `samplepaper.tex`, `mybib.bib`, `fig1-5.pdf`, `src/results`.
- The `knowledge-base-template` content.
- The ML/MLCONF profiles and the `ml` discipline card.
- The soccer-specific peeves in the `editor.md` pools.
- The ML-type text in `methods-referee`.
- `domain-reviewer`'s persona.
- The `verifier` commands.
- The deductions table in `quality-gates`.
- The tolerance rows and passport examples in `replication-protocol`.
- `WORKFLOW_QUICK_REF`'s non-negotiables.

**Fix before porting:**
- Create the missing `templates/` and checker scripts, or remove the references to them.
- Unify the Python toolchain story.
- Change `globs:` to `paths:`.
- Add `.py` to verify-reminder and fix the `.R` case bug.
- Decide where state lives (home directory vs `.claude/state/`) and make `.gitignore` match.
- Drop the dangling settings keys (`--strict-passport`, `verifyClaims.allowHighWarn`).
