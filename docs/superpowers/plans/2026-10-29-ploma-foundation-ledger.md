# SDD ledger — plan: docs/superpowers/plans/2026-10-29-ploma-foundation.md
Spec: docs/superpowers/specs/2026-10-29-ploma-design.md (review changes folded in at f1664c0). Branch: main (working agreement in BRIEF §10 and Marc: small commits on main). Models: opus for implementers and reviewers (Marc, 2026-10-29).

## Pre-flight scan
| Rows | Produces vs consumes | Finding |
|---|---|---|
| T1 conftest vs T3/T4 | `sample_paper` fixture defined T1, example created T4 | fixture must skip when example absent; T3 xfail markers removed in T4 |
| T3/T4 vs T10/T14/T15/T19/T20 | tests use `cfg`, `onboarded_sample` fixtures | no task defines them -> R1 |
| T3 validate vs T4 sample/T14 doctor | path checks on `build.pdf`, `build.log`, `outputs.dir` | outputs do not exist before compile -> R2 |
| T6 internal | interface says PASS/WARN/FAIL/SKIP, rule text says over 0 PASS, over>=1 FAIL | WARN never produced -> R3 |
| T9 internal | `next_stage(st, None)` expected "compile"; rule says no config -> onboard | contradiction -> R4 |
| T14 vs T9/T10 | doctor state group on a sample with no gate yet | severity unspecified; READY test needs it non-WARN -> R5 |
| T14 dependencies vs onboarded_sample | superpowers missing is WARN, READY test expects no WARN | -> R1 fixture enables superpowers |
| T14 vs T17 | project-files group needs render_all | SKIP until T17 as plan says |
| T17 internal | test expects `results/README.md` created-once; spec says `<outputs.dir>/README.md` (quality_reports) | -> R6 |
| T15/T16 vs global | hooks silent without config; SessionStart prints line only when .tex nearby | consistent after f1664c0 |
| T11 vs T13 | venues_for_class / CLASS_TO_VENUE need profile keys | T11 must not import profiles at module import for test isolation; options list from profiles when available else CLASS_TO_VENUE -> R7 |
| T18 vs global | HIDDEN lists skills absent in m1 | lint checks existing dirs only; fine |
| T2-T20 | python floor 3.10 in CI | use `from __future__ import annotations`; no 3.11-only stdlib (tomllib not needed) |
| All | `extraction/` not referenced by shipped code | sources may be READ while porting; never imported or path-referenced |

## Rulings
- Ruling R1: tests/conftest.py gains fixtures `cfg` (= ploma_config.load(sample_paper)) in T4 and `onboarded_sample` in T14 (sample_paper + `.claude/settings.json` enabling `superpowers@claude-plugins-official` + a PDF at build.pdf newer than all sources + `.gitignore` covering `.ploma/` and session logs; T17 extends it by applying project_files) — plan names fixtures nobody defines; the spec's READY criterion decides contents — cost if wrong: fixture churn in T17.
- Ruling R2: `ploma_config.validate` checks existence only for inputs (document.main, document.root, build.bib_files, build.cwd, reviews dir if glob has a fixed prefix, pipeline.run_from, pipeline.outputs_dir); outputs (build.pdf, build.log, outputs.dir) are not path-checked — outputs legitimately do not exist before the first compile — cost if wrong: a typo in build.log goes unflagged until compile.
- Ruling R3: `pdf_pages.budget_report` statuses are PASS (pages <= budget), FAIL (pages > budget), SKIP (budget None); no WARN — the plan's rule text is authoritative over its interface line — cost if wrong: trivial.
- Ruling R4: `state.next_stage(st, cfg)` returns "onboard" when cfg is None and no events, else "compile" before any event; T9 test passes cfg — spec §6.2 "before any event, onboard if no config" — cost if wrong: trivial.
- Ruling R5: doctor `state` group: gate missing or stale is INFO (the commit gate enforces, doctor reports); override streak >= 2 WARN; stage recommendation INFO — spec §9 groups list state without severity; READY must be reachable — cost if wrong: doctor too quiet about a stale gate.
- Ruling R6: T17 test expects `quality_reports/README.md` (outputs.dir default), not `results/README.md` — spec §8 `<outputs.dir>/README.md`; the sample's `results/` is pipeline.outputs_dir — cost if wrong: none.
- Ruling R7: inventory gap options for venue.profile come from `profiles.venues_for_class` when T13 has landed; T11 implements a local fallback using CLASS_TO_VENUE plus generic-journal/generic-conference, and T13 switches inventory to profiles (one-line change, covered by T11's existing test) — tasks ordered T11 before T13 — cost if wrong: one extra edit in T13.

## Progress
Task 1: complete (commits f1664c0..d978fd4, review clean)
- Ruling R8: keep hooks/hooks.json as `{"hooks": {}}` from Task 1 — plugin.json must reference it and validate fails without it; Task 15 treats it as a modify — cost if wrong: none.
- Ruling R9: keep the generated .claude-plugin/icon.png — it clears validate's ICON_MISSING warning; Marc may replace it before any public release — cost if wrong: a cosmetic icon swap.
Task 1: minor (deferred): test_every_skill_dir_has_skill_md iterates files too (plan-mandated); fix with is_dir() in lifecycle Task 2 when _shared lands
Task 1: minor (deferred): CI installs unpinned pytest
Task 1: minor (deferred): README lifecycle table lists skills not yet built; Task 18/21 must reconcile
Ruling R10: Tasks 2 and 3 dispatched as one unit (one implementer, one review) — Task 3 consumes Task 2's loader directly and both are single-module script work — cost if wrong: a larger review surface for one reviewer.
Tasks 2-3: implemented (commits d978fd4..a990a0e), DONE_WITH_CONCERNS; rulings on concerns:
- Ruling R11: worst() order FAIL > WARN > INFO > SKIP > PASS stands — only used to pick a display status; doctor verdict uses its own ladder where INFO/SKIP never count — cost if wrong: none for verdicts.
- Ruling R12: pipeline paths checked only when pipeline.enabled — a disabled block is inert by spec §5 — cost if wrong: stale paths in a disabled block go unflagged.
- Ruling R13: a missing reviews directory is WARN, not FAIL — reviews are optional input (a first submission has none) — the fix round must change it — cost if wrong: none.
- Ruling R14: unknown-key WARN via additionalProperties stands — catches typos in hand-edited ploma.yaml; ploma.d/ overrides are separate files so no false positives — cost if wrong: a WARN on a deliberate extension key.
- Ruling R15: load() deriving root, slug, cwd, pdf, log from document.main stands provided explicit values always win — fills spec defaults — cost if wrong: surprising derived values; reviewer checks precedence.
- Ruling R16: Task 4 removes all three xfail markers (not two).
Tasks 2-3: review needs fixes (2 Important: R13 severity; dump crash on '>' strings) — fix round 1 dispatched, FIX_BASE a990a0e
Tasks 2-3: minor (deferred): _yamlmini refuses escaped quotes inside double-quoted strings (fails loudly)
Tasks 2-3: minor (deferred): \u/\x escapes left literal; 012/0x1F stay strings; dump writes 012, =, << unquoted
Tasks 2-3: minor (deferred): document.main "" or a directory validates; derived-path FAILs cascade when main is missing
Tasks 2-3: minor (deferred): thin refusal tests (block scalars, separators, later-line alias); two loose assertions
Tasks 2-3: minor (deferred): misleading multi-line plain scalar message; lenient accepts PyYAML rejects; LOADER fixed at import
Tasks 2-3: fix round 1/5 (2 addressed, 0 open; commits a990a0e..9111660)
Task 2: complete (commits d978fd4..9111660, review clean)
Task 3: complete (commits d978fd4..9111660, review clean)
Task 4: implemented (commits 9111660..e434c95), DONE_WITH_CONCERNS
- Ruling R17: crlf_wrapped.log stays realistic (pdflatex wraps the box-content line, not the Overfull header). Task 5 adds a wrapped-warning case where line joining matters: a `LaTeX Warning: Citation ... undefined on input line N.` split at column 79, which pdflatex really produces for long keys — cost if wrong: line-joining logic tested on warnings only.
- Ruling R18: error.log holding both error forms stands; Task 5 asserts on errors[0] (method.tex:42) and on len(errors) == 2 — cost if wrong: none.
- Ruling R19: Task 5 adds `.gitattributes` with `tests/fixtures/logs/*.log -text` so CRLF fixtures survive autocrlf clones — cost if wrong: none.
Task 4: complete (commits 9111660..e434c95, review clean)
Task 4: minor (deferred): a 105-char log line is unwrapped in every log fixture (inconsistent with the 79-col wrap); harmless for a parser joining exact-79 lines
Task 4: minor (deferred): error.log line numbers (42) exceed sample file lengths (plan-mandated); tabular "lines 11--20" off by one
Task 4: minor (deferred): cosmetic log/paper mismatches (fonts, figure width)
Task 4: minor (deferred, milestone 2): baseline cells 0.72/0.76 match no metrics.json key, so consistency will WARN twice on the sample; lifecycle Task 3 eval must expect it or add baseline keys
Ruling R20: Tasks 5 and 6 dispatched as one unit — two small independent single-module scripts with their own tests — cost if wrong: larger review surface.
Tasks 5-6: implemented (commits e434c95..7c867f5), DONE_WITH_CONCERNS
- Ruling R21: the extra test test_wrapped_citation_key_split_across_lines stands (it falsifies the joiner; R17's test did not) — falsifiable-checks rule — cost: none.
- Ruling R22: 79-column join only (pdflatex default max_print_line); other widths unsupported in v0.1 — cost if wrong: missed warnings on custom-configured TeX installs.
- Ruling R23: compressed object streams without pdfinfo give (None, reason) — doctor warns when pdfinfo is absent anyway — cost if wrong: page budget SKIP on such PDFs without poppler.
Task 5: complete (commits e434c95..750024a, review clean)
Task 6: complete (commits 750024a..7c867f5, review clean)
Task 5: minor (deferred, final review should consider fixing): test_wrapped_overfull_line does not falsify unwrap; assert context has no stray \r
Task 5: minor (deferred, likely to bite non-English labels): wrap width counted in chars, pdflatex counts bytes; unwrap on bytes before decoding
Task 5: minor (deferred, likely to bite every fatal run): "!  ==> Fatal error occurred" counted as an extra error; exclude ^!\s+==>
Task 5: minor (deferred): l.<n> lookup window does not stop at a path:N: error
Task 6: minor (deferred): pdftotext non-zero exit reads as "not found" for every heading
Task 6: minor (deferred): _run text=True uses locale encoding; set utf-8 errors=replace
Task 6: minor (deferred): scan overcounts PDFs with incremental updates
Task 7: implemented (commits 7c867f5..fe7dcb2), DONE_WITH_CONCERNS
- Ruling R24: callers (Tasks 11, 14, 19, 20) pass absolute bib paths resolved from the repo root via ploma_config.resolve()["_paths"]["bib_files"]; resolve_bib_files' main-dir resolution applies only to discovered \bibliography names — cost if wrong: a wrong bib path when main is not at the root.
- Ruling R25: duplicate keys are a real BibTeX defect (bibtex reports "Repeated entry" and keeps the first); add `bib.duplicate_key.<key>` WARN in check_entries across all files — carried into the fix round or a follow-up commit in this task — cost if wrong: one extra finding id.
- Ruling R26: keys split across lines, nested braces in [...] and brace-less \input stay unsupported in v0.1 — rare in practice — cost if wrong: a missed citation reported as unused.
Task 7: review needs fixes (1 Important: R25 duplicate keys) — fix round 1 dispatched, FIX_BASE fe7dcb2
- Ruling R27: cite command set extended (\citeyearpar, capitalised natbib/biblatex forms, \footcite, \cites multi-arg, \fullcite, \smartcite, \supercite, \citetitle, \citenum) — promoted from reviewer minor: a key cited only through these escapes the required bib gate — cost if wrong: none.
- Ruling R28: bib.cite_style_mix = natbib-only command mixed with biblatex-only command; \cite neutral — promoted from reviewer minor: the brief's rule warned on every normal biblatex paper — cost if wrong: none.
Task 7: minor (deferred): ')' inside a quoted value in a paren-delimited entry closes the entry early
Task 7: minor (deferred): edit-distance near-miss path untested; threshold 2 too loose for very short keys
Task 7: minor (deferred): bib.file_missing id uses file name only (collision across dirs)
Task 7: minor (deferred): \input{fig.tikz} not found (LaTeX falls back to bare name)
Task 7: minor (deferred): % inside \url{} treated as comment
Task 7: minor (deferred): \citealt is natbib-only but treated as neutral in cite_style_mix
Task 7: fix round 1/5 (3 addressed, 0 open; commits fe7dcb2..08ad889)
Task 7: complete (commits 7c867f5..08ad889, review clean)
Task 7: minor (deferred): \cites swallows any {...} group after it, e.g. \cites{a} {bold}
Task 8: implemented (commits 08ad889..5858ec0), DONE_WITH_CONCERNS
- Ruling R29: DOI 404 or unreachable falls back to title search; a title match after a DOI 404 is `partial` with evidence naming the dead DOI — the bib's DOI is wrong and the author should see it — cost if wrong: none.
- Ruling R30: DOI hit with title ratio 0.6-0.90, or with no title, is `partial` — between verified and mismatch — cost if wrong: none.
- Ruling R31: title search stops at the first source scoring >= 0.90 — saves lookups — cost if wrong: a partial that a later source would have verified.
- Ruling R32: a hit LACKING year or authors does not count as a mismatch; that field is simply not checked (absent data is not contradiction) — implementer chose the opposite; the fix round changes it — cost if wrong: a few verified results that are less certain.
- Ruling R33: extra --openalex-key/--s2-key flags with env defaults stand — the skill passes userConfig values as args — cost if wrong: none.
- Ruling R34: cache keyed by DOI or title; unreachable/skipped never cached; max_lookups counts network lookups only — sensible — cost if wrong: none.
Task 8: review needs fixes (3 Important: R32 inverted; Crossref subtitle false mismatch; cached verdicts outlive bib fixes) — fix round 1 dispatched, FIX_BASE 5858ec0
- Ruling R35: any exception parsing a source response = that source failed; run guards per entry and always saves the cache — promoted minor: one malformed response lost the whole run's cache — cost if wrong: none.
- Ruling R36: strip <...> tags from titles before normalising — promoted minor: JATS markup is common in Crossref/OpenAlex titles — cost if wrong: none.
Task 8: minor (deferred): DataCite DOIs (arXiv 10.48550, Zenodo) 404 on Crossref and become partial; consider doi.org/DataCite check
Task 8: minor (deferred): among several >=0.90 hits, prefer one with no problems over highest ratio
Task 8: minor (deferred): concurrent runs: last writer wins on the cache
Task 8: minor (deferred): imports private _norm_doi from bib_check
Task 8: fix round 1/5 (5 addressed by implementer report; re-review deferred to cover rounds 1-2 together; commits 5858ec0..f809a11)
- Ruling R37: before-colon match verifies only when at most one side has a subtitle; differing subtitles on both sides give partial — two editions share a prefix — cost if wrong: some correct entries with variant subtitles show partial.
Task 8: fix round 2/5 dispatched (empty DOI title -> partial per R30; R37)
Task 8: fix round 2/5 (7 addressed across rounds 1-2, 0 open; commits 5858ec0..145a92b)
Task 8: complete (commits 08ad889..145a92b, review clean)
Task 8: minor (deferred): a DOI that was unreachable while title search succeeded is cached as failed for 90 days, hiding a wrong DOI
Task 8: minor (deferred): main-title prefix match is broad ("Editorial: X" vs "Editorial"); tag regex can eat literal a<b c>d; en-dash/-- not treated as subtitle breaks
Ruling R38: Tasks 9 and 10 dispatched as one unit — both are small YAML/JSON state files under outputs.dir with the same conventions — cost if wrong: larger review surface.
Tasks 9-10: implemented (commits 145a92b..cbe809e), DONE_WITH_CONCERNS
- Ruling R39: override() refusing a fourth consecutive override with ValueError (CLI exit 1) stands — it is Marc's hard stop enforced at the source, not only in the skill — cost if wrong: none.
- Ruling R40: unknown skill/check/status names raise ValueError (CLI exit 2); gate statuses PASS/WARN/FAIL; required WARN passes but does not reset the streak — conservative — cost if wrong: none (compile and bib record PASS or FAIL).
- Ruling R41: gate.py importing state.py private helpers stands for now — deferred minor: move _atomic_write/_now to a shared helper when a third module needs them.
Tasks 9-10: review needs fixes (2 Important: gate fails open on invalid status; corrupt-shape files crash) — fix round 1 dispatched, FIX_BASE cbe809e
- Ruling R42: git check-ignore -z --stdin, no strip — promoted minor: accented filenames are plausible for this author — cost if wrong: none.
Tasks 9-10: minor (deferred): manuscript_sha crashes on unreadable files, broken symlinks, non-UTF-8 names
Tasks 9-10: minor (deferred): .tex/.bib under outputs.dir are hashed when it sits inside document.root
Tasks 9-10: fix round 1/5 (3 addressed, 0 open; commits cbe809e..5786818)
Task 9: complete (commits 145a92b..5786818, review clean)
Task 10: complete (commits 145a92b..5786818, review clean)
Task 11: implemented (commits 5786818..454fe54), DONE_WITH_CONCERNS
- Ruling R43: article -> generic-journal recommended for the sample stands (it is a gap the user answers; both options offered) — cost if wrong: one extra click.
- Ruling R44: a line merely naming pdflatex/bibtex/biber counts as restating build facts — such lines do restate the engine/bib tool that ploma.yaml owns; on traces all six flagged rules are legacy anyway — cost if wrong: a noisy retirement checklist on non-traces repos.
- Ruling R45: extra keys uses_author_year and _root, and skipping all hidden dirs, stand — cost if wrong: none.
Task 11: minor (deferred): \author{Anonymous ...} uncommented is not treated as anonymized
Task 11: review needs fixes (3 Important: anonymity; false ambiguity from standalone/subfiles and Makefile comments; no main override) + spec gap root code markers — fix round 1 dispatched, FIX_BASE 454fe54
- Ruling R46: build file preference: main's dir, then one naming the main, then root; a MAIN-less root Makefile is not used when the main lives in a subdirectory — promoted minor — cost if wrong: a repo whose root Makefile really builds a subdirectory paper gets build kind None and one gap.
- Ruling R47: inventory gains main= override (and --main) so onboard re-runs after the document.main gap — reviewer finding 3, plan interface extended — cost if wrong: none.
Task 11: minor (deferred): tree walked three times; rglob on results/outputs uncapped; full reads of large .tex files
Task 11: minor (deferred): wrapped prose like "make claims traceable" can match the make rule
Task 11: minor (deferred): unused repo_root fixture in test_legacy_harness_detected
Task 11: fix round 1/5 (5 addressed per report; re-review deferred to cover rounds 1-2; commits 454fe54..1817ccf)
- Ruling R48: sample ploma.yaml anonymized: true (its \author is "Anonymous Author") — consistency with the R1-round anonymity rule — cost if wrong: none.
Task 11: fix round 2/5 dispatched (R46 clarified: an outside build file is used only when it names THIS main; sample anonymized true)
Task 11: fix round 2/5 (6 addressed across rounds 1-2, 0 open; commits 454fe54..5b1ab1f)
Task 11: complete (commits 5786818..5b1ab1f, review clean)
Task 11: minor (deferred): --main accepts paths outside the repo
Task 11: minor (deferred): bare "MAIN =" line can read the next line's token (use [ \t]*)
Task 11: minor (deferred, worth fixing before traces test): a Makefile in the main's dir naming a DIFFERENT main is still chosen (make would build other.pdf)
Ruling R49: Tasks 12 and 13 dispatched as one unit — receipt is a 13-line brief; both are data/loader modules — cost if wrong: larger review surface.
Tasks 12-13: implemented (commits 5b1ab1f..9afb9f1), DONE_WITH_CONCERNS
- Ruling R50: the venue.profile page-budget gap recommends the recommended profile's page_budget (plan Task 11 text); the inventory test expectation changes for llncs (12) — implementer kept None to protect an old test; plan text is authoritative — must be fixed in this task's fix round — cost if wrong: none.
- Ruling R51: one ML paper type stands (only one has source weights) — cost if wrong: thinner methods-referee calibration for non-empirical ML papers until milestone 2 adds types.
- Ruling R52: the banned "llncs" term excludes the venue key: pattern `llncs(?!-conference)` — keys are identifiers, not domain prose — cost if wrong: none.
- Ruling R53: generic-conference with null budget gives SKIP on the page check — correct per R3 — cost if wrong: none.
Tasks 12-13: review needs fixes (2 Important: R50 page-budget recommendation; R52 banned regex) — fix round 1 dispatched, FIX_BASE 9afb9f1
- Ruling R54: receipt test reads the version from plugin.json — promoted minor, avoids a break at every version bump.
- Ruling R55: receipt rejects absolute and ".." paths on write and load; CLI exits 2 on OSError — promoted minor — cost if wrong: none.
Tasks 12-13: minor (deferred): receipt sha256 pattern and duplicate paths not validated
Tasks 12-13: minor (deferred): venues_for_class silently drops a malformed ploma.d override and hides the shipped profile; load_venue does not validate overrides (doctor should)
Tasks 12-13: minor (deferred): CLASS_TO_VENUE now unused (keep with a comment); springer-ml "orientation" residue; adjustments reference dimensions some disciplines lack
- Ruling R56: receipt.write rejects absolute paths (even inside root); Task 17 must pass repo-relative paths — cost if wrong: a ValueError in Task 17 if it passes absolutes.
Tasks 12-13: fix round 1/5 (4 addressed, 0 open; commits 9afb9f1..85c0629)
Task 12: complete (commits 5b1ab1f..85c0629, review clean)
Task 13: complete (commits 5b1ab1f..85c0629, review clean)
Task 14: implemented (commits 85c0629..1453925), DONE_WITH_CONCERNS
- Ruling R57: doctor importing inventory's private _superpowers/_figures stands (as R41) — avoids the full walk — deferred minor: promote to public names later.
- Ruling R58: project-files.gitignore WARN stays and Task 17 keeps it — spec §9 item 5 — cost if wrong: none.
- Ruling R59: a FRESH gate FAIL (a required check failed on the current manuscript) is WARN in doctor, not INFO; missing or stale stays INFO (R5) — a known failing compile or bib should not read as READY — fix in this task's round — cost if wrong: doctor shows READY_WITH_WARNINGS after a failed compile.
- Ruling R60: blank line before group headings and the exec bit on doctor.py stand — cosmetic.
Task 14: review needs fixes (1 Important: R59) — fix round 1 dispatched, FIX_BASE 1453925
- Ruling R61: unexpected exceptions in config, toolchain, manuscript groups are FAIL <group>.error — promoted minor: a crash must not turn NOT_READY into READY_WITH_WARNINGS — cost if wrong: a bug in doctor itself shows NOT_READY.
- Ruling R62: missing document.root gives SKIP manuscript.pdf_fresh; gate.check wrapped alone so state findings survive a sha error — promoted minor.
Task 14: minor (deferred): bib FAIL summary names only missing and file_missing kinds
Task 14: minor (deferred): _ignored_by is a simple matcher (globs give a false WARN) until Task 17
Task 14: minor (deferred): test_render_default_which uses the real which and home
Task 14: fix round 1/5 (3 addressed, 0 open; commits 1453925..2c0db98)
Task 14: complete (commits 85c0629..2c0db98, review clean)
Task 14: minor (deferred): failed-check list parses ": FAIL" substring from gate reasons
Ruling R63: Tasks 15 and 16 dispatched as one unit — all hooks share hooks/_hookutil.py and hooks/hooks.json — cost if wrong: larger review surface.
Tasks 15-16: implemented (commits 2c0db98..c9fbc34), DONE_WITH_CONCERNS
- Ruling R64: code written before tests; RED evidence obtained by moving the implementation aside — accepted (the tests are shown to fail without the code) — cost if wrong: weaker evidence that tests drove design.
- Ruling R65: ploma_config.summary must omit keys whose value is None (it prints "None" for pipeline.rerun) — a Task 3 defect surfaced here; fix in this unit's fix round or a follow-up commit — cost if wrong: noise in every session's context.
- Ruling R66: SubagentStart silent without ploma.yaml; resume block leaves pre-compact-state.json in place (pre_compact overwrites it) — cost if wrong: an old resume block shown once after a non-compact resume.
Tasks 15-16: review needs fixes (2 Important: R65 None in summary; context monitor cache never resets) — fix round 1 dispatched, FIX_BASE c9fbc34
- Ruling R67: project dir = CLAUDE_PROJECT_DIR, then stdin cwd, then getcwd, then walk up <= 4 levels (stop at .git) for ploma.yaml — supersedes my earlier resolution (cwd first) that made hooks silent after a cd — cost if wrong: a nested repo picks up a parent's ploma.yaml (bounded by .git stop).
- Ruling R68: git timeouts 5 s; manuscript_sha prunes hidden, node_modules, .venv, venv, __pycache__, build, dist; status imports inside try — hook must finish inside its 10 s timeout — cost if wrong: a .tex under a pruned dir is not hashed.
- Ruling R69: plan status read from the first **Status:** line in both hooks — consistency — cost if wrong: none.
Tasks 15-16: minor (deferred): PreCompact {"decision": "block"} support unverified in Claude Code (opt-in only)
Tasks 15-16: minor (deferred): rules/reference/replication-tolerances.md names scripts/consistency.py, which lands in milestone 2
Tasks 15-16: fix round 1/5 (6 addressed, 0 open; commits c9fbc34..70ecd4c)
Task 15: complete (commits 2c0db98..70ecd4c, review clean)
Task 16: complete (commits 2c0db98..70ecd4c, review clean)
Tasks 15-16: minor (deferred): walk-up can adopt a non-git parent's ploma.yaml when the project dir is not a git repo
Tasks 15-16: minor (deferred): _find_project_dir copied into six hook files (guarded by an AST equality test)
Task 17: implemented (commits 70ecd4c..0a655c0), DONE_WITH_CONCERNS
- Ruling R70: .gitignore coverage also accepts an ancestor directory entry (e.g. `quality_reports/` covers `quality_reports/session_logs/`) and `<dir>/**` forms; fix in this task's round — a repo ignoring the whole outputs dir must not get a false WARN — cost if wrong: none.
- Ruling R71: receipt records the current sha after apply (hand-edited created-once files then read unchanged) stands — created-once files are user-owned after seeding — cost if wrong: doctor stops telling the user they edited a created-once file, which is their right anyway.
- Ruling R72: project_files importing state's private helpers stands (R41 pattern).
Task 17: minor (deferred): CRLF CLAUDE.md/.gitignore rewritten with LF on merge
Task 17: review needs fixes (1 Important: R70 not implemented, test pinned the opposite) — fix round 1 dispatched, FIX_BASE 0a655c0
- Ruling R73: markers inside fenced code blocks are ignored — promoted minor: otherwise onboard rewrites a user's example or blocks forever — cost if wrong: none.
- Ruling R74: created-once write skipped when the file exists at apply time — promoted minor: data loss between plan and approval — cost if wrong: none.
- Ruling R75: outputs.dir absolute or with ".." rejected before any write — promoted minor: partial apply outside the repo — cost if wrong: none.
- Ruling R76: a generated ploma-pipeline.md is removed (plan action "remove") when the pipeline is disabled, only if it carries the generated marker line; doctor WARN project-files.stale — promoted minor: stale facts in an always-loaded rule — cost if wrong: none.
Task 17: minor (deferred): paths ["**"] makes the pipeline rule effectively eager when run_from is "."
Task 17: minor (deferred): ploma-state.yaml always plans as skip_hand_edited (label misleading)
Task 17: fix round 1/5 (5 addressed, 0 open; commits 0a655c0..1c6dafa)
Task 17: complete (commits 70ecd4c..1c6dafa, review clean)
Task 17: minor (deferred): receipt.path does not use the outputs_dir guard (read-only exposure); negation after a wildcard ancestor still reported covered; "remove" diff header cosmetic
- Ruling R77: Task 18 also fixes the deferred Task 11 minor: a build file in the main's directory whose MAIN names a DIFFERENT main is not used (kind None) — onboard is the first consumer and make would build the wrong PDF — cost if wrong: one more gap for such repos.
Task 18: implemented (commits 1c6dafa..6f08d97), DONE_WITH_CONCERNS; onboard dry run on a scratch copy cost $0.85, proposed main.tex, wrote nothing
- Ruling R78: project_files --config PATH|- and ploma_config.loads stand — needed so onboard can show the plan before writing ploma.yaml (spec: nothing written before approval) — cost if wrong: none.
- Ruling R79: eval cases reach the sample through per-case symlinks plus scaffold.sh — add_dirs cannot use ".." — cost if wrong: evals need --scaffold to exercise the paper.
- Ruling R80: help lists compile and validate-bib as installed ahead of Tasks 19-20 — they land in this milestone before any release — cost if wrong: none if Tasks 19-20 complete.
Task 18: review clean (Approved, 0 Critical/Important); FIX_BASE 6f08d97
- Ruling R81: follow-up round on onboard prose before the real-paper test: null keys never re-asked; step 7.1 Edit-only note for absorption; zero main candidates stop and ask; remove rows shown; profiles lookup with project root; quote $ARGUMENTS in doctor; status layout gains override streak — reviewer minors promoted because traces-16 runs onboard next — cost if wrong: none.
Task 18: minor (deferred): tool_used Skill grader may not register on slash-command prompts; status newest-first relies on Glob order; context monitor tool_calls line only in fallback mode; project_files --config relative to cwd not --root (undocumented)
Ruling R82: Tasks 19 and 20 dispatched as one unit (compile and validate-bib: script + skill + eval each, same pattern) while the Task 18 follow-up re-review (read-only) runs — cost if wrong: a Task 18 re-fix touching skills/ could conflict; the follow-up only edits skills/onboard, doctor, status.
Task 18: fix round 1/5 (R81 follow-up: 6 addressed, 0 open; commits 6f08d97..53d8d82)
Task 18: complete (commits 1c6dafa..53d8d82, review clean)
Task 18: minor (deferred): doctor skill command template is single-word "$ARGUMENTS" while the note says pass --json and path as two quoted words
Tasks 19-20: implemented (commits 53d8d82..ff5e83a), DONE_WITH_CONCERNS
- Ruling R83: when page_budget_includes_refs is false and the reference start cannot be found (no pdftotext or no heading), the budget is UNVERIFIED: compile stays PASS on that criterion, the report states the total pages and that the budget could not be checked, and the gate entry carries budget_unverified: true — a check that cannot measure must not fail the required gate (falsifiable-checks); traces' host has pdftotext — fix in this unit's round — cost if wrong: an over-budget paper passes the gate on a host without poppler.
- Ruling R84: missing log or PDF after a zero exit is FAIL — a wrong build.log path must not pass unchecked — cost if wrong: none.
- Ruling R85: sensitive API keys never appear in skill text; the validate-bib skill passes only --mailto; the script reads keys from CLAUDE_PLUGIN_OPTION_OPENALEX_API_KEY / CLAUDE_PLUGIN_OPTION_SEMANTIC_SCHOLAR_API_KEY and plain env — secrets must not enter model context — fix in this round — cost if wrong: lookups run keyless if the env var is not exported to Bash.
- Ruling R86: validate_bib passes cache_path <root>/.ploma/cite_lookup.json when CLAUDE_PLUGIN_DATA is unset (not cwd) — fix in this round — cost if wrong: none.
- Ruling R87: compile eval accepts a correctly reported FAIL on a TeX-less machine — traces-16 exercises PASS for real.
Tasks 19-20: review needs fixes (4 Important: R83, R85, R86 not done; timeout leaves orphaned grandchildren) — fix round 1 dispatched, FIX_BASE ff5e83a
- Ruling R88: a log older than the build start is FAIL "log was not written by this build" — promoted minor: a stale clean log must not pass the required gate — cost if wrong: a build that legitimately does not touch an unchanged log (none in practice; pdflatex always rewrites it).
- Ruling R89: doi_lookups_per_run 0 means no lookups; non-integer is a usage error; mismatch/partial tested — promoted minor.
Tasks 19-20: minor (deferred): clean step only detects make as the first word (cd x && make falls back to latexmk -c); validate_bib uses bib_check._norm_doi (private)
Tasks 19-20: fix round 1/5 (7 addressed, 0 open; commits ff5e83a..9bae499)
Task 19: complete (commits 53d8d82..9bae499, review clean)
Task 20: complete (commits 53d8d82..9bae499, review clean)
Tasks 19-20: minor (deferred): R88 1 s mtime tolerance can misfire on FAT/exFAT or NFS clock skew; consider 2 s or a marker file
Tasks 19-20: minor (deferred): lookup_cap validated even on structural/--skip-doi runs
Tasks 19-20: minor (deferred): R85 relies on CLAUDE_PLUGIN_OPTION_* reaching Bash (unverified); worst case keyless lookups
- Ruling R90: Task 21 commits but does not push; the push and the traces-16 hand-off happen after the final whole-branch review — pushing before review would hand traces-16 unreviewed integration — cost if wrong: a short delay.
Task 21: implemented (commits 9bae499..10806f6), DONE_WITH_CONCERNS; eval run once: 0/6 cases, score 0.11, $2.09 — cause is eval setup (no --scaffold/--allow-tools; runner refuses per-case symlinks), not the skills
- Ruling R91: R79 was wrong: eval cases must not use symlinks; the fix wave replaces them with case.yaml scaffold_script copies and documents the eval command (with --scaffold and --allow-tools 'Bash(python3 *)'); evals/results/ gitignored — cost if wrong: another eval run.
Task 21: review folded into the final whole-branch review (docs-only diff)
Final review: With fixes — 2 Critical (compile FAIL on up-to-date make, R88+R84 wrong under make; semantic "missing" FAIL on @misc/tech reports), 5 Important (PyYAML line wrap unreadable by yamlmini; slow semantic run loses work; DataCite DOIs 404 on Crossref (R29 premise wrong); fatal error double count; templates point at uninstalled skills), eval fix spec. One fix wave dispatched, FIX_BASE 10806f6.
- Ruling R92 (supersedes R88): exit 0 with an un-rewritten log is PASS "build was up to date" when log and PDF are newer than every source; else FAIL "make did not rebuild; run /ploma:compile --clean"; --clean on make builds runs `make -B <target>` (force) instead of make clean — real make skips up-to-date targets — cost if wrong: none.
- Ruling R93 (amends R29): Crossref 404 on a DOI checks DataCite before falling back to title search.
- Ruling R94: lookup `missing` is FAIL only when all three sources answered and the type is article/inproceedings/book/incollection/inbook/phdthesis; otherwise WARN "not found in indexes" — misc, techreport, online, software entries are legitimately absent — cost if wrong: a fabricated @misc reference passes as WARN.
Final fix wave: implemented (commits 10806f6..af6c868), DONE_WITH_CONCERNS; smoke eval could not start (sandbox needs socat, not installed; no passwordless sudo) — $0
- Ruling R95: after the semantic time budget, cached entries are still judged (no network) and only network lookups are skipped — strictly more information at no cost — cost if wrong: none.
- Ruling R96: a DOI absent from Crossref and DataCite with no title is WARN not_indexed — nothing left to search — cost if wrong: a bogus DOI-only entry is WARN, not FAIL.
- Ruling R97: R92's up-to-date check covers .tex/.bib only — matches what make itself decides from the Makefile's prerequisites — cost if wrong: a figure-only change reported up to date when make also skipped it.
Final fix wave: re-review clean (10 findings addressed, 0 Critical/Important new; commits 10806f6..af6c868)
Final review: minor (deferred): classic-error attribution ignores closing parens (only without -file-line-error); not_indexed summary wording on the DOI-fallback path; a non-prerequisite .tex newer than the log gives "make did not rebuild" (recover with --clean)
Final review: minor (deferred): help lifecycle table rows lack planned markers; newline-containing strings dumped by PyYAML are unreadable by yamlmini; strict-type entry is missing (FAIL) when only the DOI path failed but all title searches answered
Milestone 1: complete.
