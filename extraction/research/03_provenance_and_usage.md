# Provenance and real-world usage of the traces academic harness (extracted 2026-10-29)

**Repo:** `/home/marc/Development/dshs/mlsa/traces` (paper: "Capturing Team Strategy in European Football via Process Mining", LLNCS, Springer Machine Learning journal target; previous ADS-track reviews in `review/review1-3.md`).

## 1. Where it came from

**Upstream: `pedrohcgs/claude-code-my-workflow`** (GitHub). The commit body of `bab1fc2` says so directly:

> "Add academic Claude Code harness (.claude/)
>
> Vendor a curated, adapted subset of the **pedrohcgs/claude-code-my-workflow** template, retuned for this project: process mining / ML / Springer LLNCS.
> - 20 slash-skills: /compile-latex (wired to manuscript/Makefile, pdflatex not xelatex), /review-paper (--peer ML journal profile), /respond-to-referees (against review/review1-3.md), /validate-bib (Crossref/Semantic Scholar/OpenAlex, all free/keyless), /audit-reproducibility (Python pipeline), plus proofread, verify-claims, seven-pass-review, deep-audit, devils-advocate, lit-review, research-ideation, interview-me, data-analysis, learn, etc.
> - 9 agents incl. python-reviewer (knows the TAGS_FILE import-time, action##zone, and coordinate-orientation gotchas); peer-review trio (editor + 2 referees).
> - 19 rules, ML journal profiles, and the 6 upstream hooks (audited: no network/exec, local state only).
> - settings.json hardened: no bypassPermissions, **/.env* denied, conservative Bash allow-list."

(Marc Garnica Caparrós, Jun 4 2026 15:02, Co-Authored-By Claude Opus 4.8.)

- **Upstream version:** the vendored files mention upstream releases up to **v1.9.0** (for example "Passport-mode (v1.9.0)" in `audit-reproducibility/SKILL.md:172`). Skill frontmatter reads `author: Claude Code Academic Workflow` / `version: 1.0.0` (checkpoint, compress-session, context-status, deep-audit, learn, promote-memory).
- **Leftovers from upstream:** the vendoring did not clean everything.
  - `checkpoint/SKILL.md:137-142` still has upstream example paths such as `quality_reports/plans/2026-04-27_v180-polisci-apr2026.md` and branch `feat/v1.8.0-polisci-apr2026`.
  - `audit-pet-peeves.md` refers to upstream PRs #87–#92 and the CHANGELOG.

**Other attributions inside the harness:**

| Source | Where it is credited |
|---|---|
| Hugo Sant'Anna, **clo-author** (`github.com/hugosantanna/clo-author`, v4.2.0) | `agents/editor.md:8`, `agents/domain-referee.md:8`, `agents/methods-referee.md:8`, `references/journal-profiles.md:1`, `skills/checkpoint/SKILL.md:11`, `skills/review-paper/SKILL.md:50` ("with permission"), `rules/content-invariants.md:11` |
| Chris Blattman, **claudeblattman v2.1** (`github.com/chrisblattman/claudeblattman`) | `references/prompt-formatting-core.md:5`, `skills/promote-memory/SKILL.md:11` |
| **Imbad0202/academic-research-skills** ("Material Passport") | `rules/replication-protocol.md:179` |
| Michael Ewens gist (`gist.github.com/michaelewens/9a1bc5a97f3f9bbb79453e5b682df462`) | `hooks/log-reminder.py:18` |
| Dhuliawala et al. 2023, Chain-of-Verification (arXiv:2309.11495) | `rules/post-flight-verification.md:15`, `agents/claim-verifier.md:8` |
| **obra/superpowers** | Installed as a plugin, not vendored. `CLAUDE.md:123-127`; `4996277` added `"superpowers@superpowers-marketplace": true` to `.claude/settings.json` |

- **No "lisa", "claude-code-templates" or "awesome" references** appear in the repo.
- **Git history:** only 4 commits. `59cbfb7` (CLAUDE.md, 108 lines) → `bab1fc2` (64 files, +8014, the whole harness) → `4996277` (settings.json +36/-9) → `f1b5773` ("chore: minor change manuscript", no body).
- **Second copy already exists:** the harness was copied and adapted again in `/home/marc/Development/dshs/grants/delphi_nba/.claude/` (a grant proposal; copy in `extraction/delphi-harness/`).
  - Renamed or added there: `compile-latex`→`compile-doc`, `respond-to-referees`→`respond-to-reviewers`, `review-paper`→`review-proposal`, `journal-profiles`→`funder-profiles`, plus a new `doc-verifier` agent.
  - Dropped there: python-reviewer, replication, audit-reproducibility, data-analysis.
  - The plan `glittery-fluttering-melody.md` says it "Supersedes the prior (completed) harness-migration plan". This copy-and-adapt step is the clearest sign that a plugin is needed.

## 2. How it has been used

**Chronology** (from `quality_reports/session_logs/2026-06-04_rr-revision-kickoff.md`, 319 lines, the only session log): planning → Phase 1 `/lit-review` → `/validate-bib --semantic` → Phase 2 pipeline work with a `python-reviewer` QA pass → Phase 3 manuscript edits → a "Full audit" on 2026-06-05 (review-paper + validate-bib + proofread + verify-claims) → targeted fixes.

| Report | Skill that made it | Format | Notes |
|---|---|---|---|
| `lit_review_process-mining-soccer-2023-2026.md` (261 l.) | `/lit-review` | Summary; Key Papers (VERIFIED), one `###` per paper with a "Contribution" bullet; TO VERIFY queue; Thematic Organization; Positioning note; Gaps & Opportunities; Next Steps; BibTeX Entries (VERIFIED); CoVe post-flight appended | Worked well. CoVe caught 2 errors ("roles paper = Aalbers & Van Haaren; OCEL 2.0 = 2024"). 9 refs went into `mybib.bib`. |
| `bib_audit_semantic.md` | `/validate-bib --semantic` | Summary table (Check × Critical/Medium/Low); **"Verdict: PASS."**; sections Structural / Citation drift / DOI verification / Style / Next steps | The earlier run found a real bug (`Fernandeznavarro2016` vs `FernandezNavarro2016`). The duplicate-title check gave 3 false positives because the "parser collided on shared booktitle/brace fields". |
| `samplepaper_report.md` | `/proofread` (proofreader agent) | Grouped HIGH (8) / MEDIUM / LOW. Each item: number, **CATEGORY**, L<line>, current text → fix. Ends with Counts and "Most impactful" | Report only, no edits (as `proofreading-protocol.md` requires). The user then approved the 8 HIGH fixes through plan `i-don-t-know-if-tender-spark.md`. Two "traceability" items (abstract numbers missing from the body) were really cross-artifact findings. |
| `verify_claims_samplepaper.md` | `/verify-claims` (fresh-context `claim-verifier`) | **"Result: PASS — 8/8 … SUPPORTED"**; table # / Claim / Verdict / Source; Advisory (LOW, non-gating) | One useful advisory: `Davis202207` venue/year drift. |
| `paper_review_samplepaper_round1.md` | `/review-paper`, "default single-pass, `--no-cross-artifact`" | Summary Assessment (recommendation); Strengths; Major Concerns MC1–3 (Dimension / Issue / Suggestion / Location); Minor mc1–7; Referee Objections RO1–5 (Why it matters / How to address); **Summary Statistics table, 1–5 per dimension, Overall 3.5 (R&R)** | All three MCs were acted on (see "What the user decided" below). The `--peer`, `--adversarial` and stress modes were never run. |
| `response_to_referees_draft.md` (215 l.) | Made in the planning phase as a "DRAFT SCAFFOLD" tracking sheet; most likely not the full `/respond-to-referees` pipeline | One `##` per reviewer, one `### R1.1 — <title>` per comment with: **Comment (quote)**, **Maps to:** C1–C8/A1–A2, **Planned revision**, **STATUS:** PLANNED / IN-PROGRESS / DONE, **Response prose:** TODO — Phase 4. Ends with a coverage checklist | Never finished; every response is still TODO. Reviewers are relabelled R1/R3/R4 to match the original "Reviewer #1/#3/#4" headers. |
| `page_budget_cut_proposal.md` | No skill (ad hoc) | Measured page-budget table, cut plan A–E ordered by value per page, before/after budget table, "What is NOT cut", Risk, Recommendation | The user overtook it ("limit was restored, proceed with all"). Cuts were later made by hand, one at a time. |
| `plans/soft-cooking-seahorse.md` (272 l.) | Plan mode (`plansDirectory: quality_reports/plans`) | Context; reviewer-consensus table C1–C8/A1–A2; MUST/SHOULD/MAY; Working style; Phases 1–4; Files; Verification; Risks; Open forks (each marked RESOLVED) | This is the main R&R plan. |
| `plans/i-don-t-know-if-tender-spark.md` | Plan mode | Targeted line-level edit plan (typos, capitalisation sweep, abstract sentence) | |
| `plans/glittery-fluttering-melody.md`, `plans/i-m-working-in-home-marc-development-dsh-elegant-fiddle.md` | Plan mode, written into this repo's plans dir but targeting **delphi_nba** | Knowledge-base seeding; reordering the proposal to an RFP's A–L structure | Shows the plans directory catching plans for other repos. |

**Never used:** no output exists from `/audit-reproducibility` (no `reproducibility_audit_*` or `reproduction_report.md`), `/seven-pass-review`, `/devils-advocate`, `/deep-audit`, `/checkpoint`, `/learn` or `/promote-memory`. **No [LEARN] entries exist:** `.claude/MEMORY.md` is an empty template. Lessons went to Claude Code auto-memory instead (`~/.claude/projects/-home-marc-Development-dshs-mlsa-traces/memory/`). Phase 4 of the plan (audit-reproducibility, adversarial review, respond-to-referees) never ran.

**What the user liked and disliked (exact quotes):**
- **Options at every fork** (`collaborative-option-driven-working-style.md`): "For any type of reasoning line that you are working, or brainstorming about different directions, always prioritize asking me and showing me different options." They want checkpoint-based execution and want to understand the why first ("what does DFG stand for").
- **Writing style** (`writing-style-direct-short.md`): "the language is correct… don't overcomplicate sentences that much, be more direct and short sentences, scientifically." No AI-slop.
- **delphi_nba memory:** no sentence-level em-dashes; the PI "explicitly rejected a plan for containing em-dashes".
- **Compact figures** (`prefer-compact-horizontal-figures.md`): horizontal pitch maps "it might occupy less page height".
- **Check before regenerating** (`check-disk-before-regenerating.md`): the user interrupted a vendoring subagent; "all good?" means assess, don't rebuild.
- Edit only the sections being worked on. The log repeatedly says "User is editing intro/related-work live — work around their live edits", and when it found contradictions it raised them as "OPEN FLAGS for author (surfaced, not silently changed)".

**What the user decided after the audit:**
- The review MCs were taken up selectively: MC1 → a new `player_fit_to_city.py` study; MC2 → one sentence of reframing, "No Inductive Miner"; MC3 → a line in future work, "no clustering study (too much space)".
- The abstract was softened to drop numbers the body did not support.

**Pain points in the logs:**
- **Number discrepancies cost a lot of time.** The "City 550 vs 294 possessions" contradiction blocked writing ("DO NOT write any N / metric into the manuscript until… settled"). It was later resolved, but a provenance note on figure scripts still flags it. This is the gap `/audit-reproducibility` was meant to close, and it was never run.
- **Docs drifted after the uv migration.** The session log notes "DOC DRIFT TO FIX". The four rules and CLAUDE.md were fixed but not committed. `WORKFLOW_QUICK_REF.md` is still stale: it says to pin in `src/requirements.txt` with pm4py 2.3.1, and to keep authors anonymized, which the user overrode.
- **The plan scaffolding said "9 pages", but the venue limit kept changing.** Page budget became a repeated manual job (17→13pp, figures cut, sections deleted). Nothing in the harness tracks the page budget.
- **A figure aspect bug lived in code, not LaTeX.** Plotly's default size squashed the pitch, and figures have no link back to the scripts that made them.

## 3. Uncommitted changes to the harness (`git diff HEAD`)

All of these come from one cause: the Python 3.9/pip → **Python 3.12/uv** migration.

- **`rules/orchestrator-research.md`:** the checklist item changes to "new deps pinned in `src/pyproject.toml` + `uv.lock` (`uv lock`)".
- **`rules/python-code-conventions.md`:**
  - Scope changes from Python 3.9 to "Python 3.12 (uv-managed)".
  - Run commands become `uv run python …`; the package is importable via `uv sync`.
  - §1 pins are now pm4py 2.7.22.4, pandas 3.0.3, numpy 2.4.6, plotly 5.24.1, kaleido 0.2.1, with `requirements.txt` "a derived export… via `uv export`".
  - The pitfalls table and §10 checklist are updated to match.
- **`rules/replication-protocol.md`:** the new stack is named; the env contract adds `STATSBOMB_DATA_DIR`; the environment section accepts "Mongo database + snapshot, or STATSBOMB_DATA_DIR JSON tree".
- **`rules/verification-protocol.md`:** `uv run python notebooks/discovery/parse_statsbomb_matches.py`.
- **`CLAUDE.md`:** Python 3.12/uv throughout, a `uv sync` setup block, `STATSBOMB_DATA_DIR`, the JSON loader added as a source, and the `/audit-reproducibility` row now cites `pyproject.toml`+`uv.lock`.

For the plugin, the point is that **project-specific facts (stack, env vars, gotchas) are hard-coded into rules and agents**, so every environment change forces edits across many files.

## 4. What the plugin must handle in the manuscript and reviews

**`manuscript/`:**
- **Files:** `samplepaper.tex` (197 lines), `mybib.bib` (64 entries, 33 cited), `fig1–6.pdf`, `llncs.cls`, `splncs04.bst`, `llncsdoc.pdf`, `history.txt`, `readme.txt`, and build artifacts. There is also an untracked `main.pdf`, a byte-identical copy of `samplepaper.pdf` (882905 bytes each).
- **Document class:** `\documentclass[runningheads]{llncs}`, `\bibliographystyle{splncs04}`, `\cite` only.
- **Makefile targets:** `build` (default; `pdflatex -interaction=nonstopmode -halt-on-error` → `bibtex` → pdflatex ×2, `MAIN = samplepaper`), `clean`, `cleanall`.
- **No `%% source:` comments.** `grep` finds only the LLNCS template comments. Figures are plain `\includegraphics{figN.pdf}`; the link to the script that made each figure exists only in the session log.
- **`*_suggestion.tex` files** are untracked, Jun 4 18:48–19:00, and no report or log mentions them. They are drop-in replacement LaTeX blocks for whole sections, probably from a separate session or tool:
  - `teamtraces_merge_suggestion.tex`: a formalism section (event tuple, possession, purpose filter Φ, ζ, trace σ, log L, M=𝒟(L)).
  - `discovery_evaluation_merge_suggestion.tex`: a merged section "Discovery and evaluation of team processes" with the HM-vs-DFG framing and metric meanings. It still says θ=0.50, which is now stale.
  - `field_partitioning_flexibility_suggestion.tex`: a paragraph making the zone partition generic ("Suggested replacement for the paragraph in … teamtraces_merge_suggestion.tex").
  - This is a "propose a section rewrite as a sibling file" pattern that the harness does not formalise.

**`review/review1-3.md`:**
- All three use the conference's fixed web-form export in plain text: a `Reviewer #N` header, a `Questions` line, then numbered prompts with answers. The prompts are 1. Relevance, 2. Summary, 3. Main strengths, 4. Main weaknesses, 5. Detailed review (one long prompt paragraph, then free text and `- ` bullets), 6. Reproducibility, 7. Deployment status, 8. Overall rating ("Weak reject: Borderline paper, tending to reject"), 9. Confidence.
- **The file names do not match the reviewer numbers:** review1 = #1, review2 = **#3**, review3 = **#4**. A plugin must read reviewer IDs from the content, not the file name.
- Comments are not numbered; the planning pass split and relabelled them (R1.1–R1.6 and so on).
- There are no markdown headings, just numbered "Q: prompt\nanswer" blocks. Other venues will use different templates, so ingestion has to be schema-agnostic.

## 5. Plugin conventions already on this machine (traces host)

**Marketplaces in `~/.claude/plugins/marketplaces/`:** academic-research-skills, cc-marketplace, claude-plugins-official, frontend-slides, impeccable, lisa, slide-generator, superpowers-marketplace. `tramat` is registered as a **local directory** marketplace (`/home/marc/Development/gemini/tramat`).

**Plugin cache (`~/.claude/plugins/cache/`):**
- `academic-research-skills/academic-research-skills` (3.9.2 installed; r2d2 has 3.23.2)
- `cc-marketplace/cc-safety-net`
- `claude-plugins-official/{atlassian, coderabbit, code-review, code-simplifier, databricks, frontend-design, hookify, playwright, posthog, sentry, skill-creator, slack, superpowers, typescript-lsp}`
- `frontend-slides`, `impeccable`, `lisa/{lisa, lisa-cdk, lisa-expo, lisa-nestjs, lisa-typescript, lisa-wiki}`, `slide-generator`, `superpowers-marketplace/superpowers`, `tramat/tramat`

**`~/.claude/settings.json`:**
- `"enabledPlugins": { "databricks@claude-plugins-official": true, "tramat@tramat": true }`
- `extraKnownMarketplaces` lists academic-research-skills (github Imbad0202), superpowers-marketplace (github obra), frontend-slides (git url), slide-generator (github geminisportsai), and tramat (`"source": "directory", "path": "/home/marc/Development/gemini/tramat"`).
- At project level, `traces/.claude/settings.json` enables `superpowers@superpowers-marketplace`.

**Best template to copy: the user's own `tramat` plugin** (same author, local directory marketplace, single-plugin repo layout). Verbatim copies of its `plugin.json`, `marketplace.json`, `hooks/hooks.json`, `UPSTREAMS.md` and README are in `extraction/references/tramat/`.

- **Tramat layout:** `agents/ commands/ docs/ examples/ hooks/ schemas/ scripts/ skills/ tests/ UPSTREAMS.md LICENSE README.md`.
- **Its `UPSTREAMS.md` convention** fits the provenance problem well: a table with columns `Upstream | What tramat took | Observed | Last reviewed`, and the rule "When updating tramat, diff each upstream since its last_reviewed and refresh the row". It already lists superpowers and lisa.
- Its skills follow a pattern of a core-rules skill plus `doctor`/`init`/`onboard` (manifest-driven, "zero edits to existing files"). That is a good model for moving the hard-coded project facts (stack, env vars, manuscript path, Makefile, reviews dir) into a per-repo manifest.

**Second reference, `marketplaces/academic-research-skills/.claude-plugin/`:**
- The marketplace entry lists skills explicitly:
  ```json
  {"name": "academic-research-skills", "source": "./", "description": "4 skills + 27 modes + Material Passport pipeline. ...", "version": "3.19.0", "license": "CC-BY-NC-4.0", "skills": ["./academic-paper","./academic-paper-reviewer","./academic-pipeline","./deep-research"]}
  ```
- Its `plugin.json` has name, version, description, author, homepage, repository, license and keywords, with no component paths.
- **License caveat:** ARS is **CC-BY-NC-4.0**, which matters if its design is vendored. The licenses of `pedrohcgs/claude-code-my-workflow` and clo-author were not checked; confirm before any public redistribution.

**superpowers-marketplace** shows the remote-source style:
```json
{"name": "superpowers", "source": {"source": "url", "url": "https://github.com/obra/superpowers.git"}, "version": "6.3.0", "strict": true}
```
