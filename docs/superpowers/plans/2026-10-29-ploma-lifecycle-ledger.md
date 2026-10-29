# SDD ledger — plan: docs/superpowers/plans/2026-10-29-ploma-lifecycle.md
Spec: docs/superpowers/specs/2026-10-29-ploma-design.md. Milestone 1 ledger (rulings R1-R97, still binding): docs/superpowers/plans/2026-10-29-ploma-foundation-ledger.md. Branch main, opus for implementers and reviewers. Rulings here continue numbering at R100.

## Pre-flight scan
| Rows | Produces vs consumes | Finding |
|---|---|---|
| T2 vs m1 tests | manifest/skill tests already skip "_" dirs (m1 T18) | T2 only adds the references; no test change -> R100 |
| T3 consistency vs gate | gate.RECOMMENDED has consistency (peer review) | consistency FAIL is a warning in v0.1; gate.record works as-is |
| T3 vs sample paper | baseline cells 0.72/0.76 match no metrics key (m1 T4 deferred minor) | add baseline keys to sample results/metrics.json so the sample is clean -> R101 |
| T10 lit-review vs schema | needs `literature.sources`; schema has additionalProperties false | T10 adds the key to schema and DEFAULTS -> R102 |
| T14 analysis-pipeline vs schema | needs `pipeline.stages` | T14 adds the key -> R102 |
| T12 learn vs project_files | learnings rule created-once, written only by learn --promote | project_files must not render it during onboard -> R103 |
| T13 commit_gate vs compile/validate_bib | prepare re-runs compile.run and validate_bib.run(semantic=False) | signatures exist (m1 T19-20); runner injection available |
| every skill task vs tests/test_skills.py | INSTALLED_M1 set gates the planned-marker test; help lists installed skills | every task adds its skills to the installed set and updates help/README/CLAUDE.md template planned markers -> R104 |
| every skill task vs evals | lint requires evals/<skill>/ with scaffold pattern, no symlinks | follow evals/doctor layout |
| T15 extraction removal | needs traces-16 confirmation; peer offline | do everything except the delete; the delete waits -> R105 |
| T1 agents vs SubagentStart | agents read "## ploma project" injected by session_context --subagent | exists (m1 T15) |
| T9 review --peer vs profiles | venue resolution via profiles.load_venue; ProfileError lists keys | exists (m1 T13) |
| T11 respond fixture | examples/sample-paper/review/review1.md has header Reviewer #3 | concern ids R3.* |
| All | Python 3.10, stdlib, no em-dashes, banned words, attribution comments carried | per milestone-1 constraints |

## Rulings
- Ruling R100: Task 2 needs no manifest test change (already skips "_" dirs) — cost if wrong: none.
- Ruling R101: Task 3 adds baseline metric keys to examples/sample-paper/results/metrics.json so consistency runs clean on the sample — resolves the m1 T4 deferred minor — cost if wrong: none.
- Ruling R102: Tasks 10 and 14 add `literature.sources` (list of dirs) and `pipeline.stages` (list of strings) to schemas/ploma.schema.json and DEFAULTS — the schema rejects unknown keys with WARN — cost if wrong: none.
- Ruling R103: the learnings rule is never rendered by onboard; only learn --promote writes it (created-once, receipt updated) — cost if wrong: none.
- Ruling R104: tests/test_skills.py INSTALLED set is renamed INSTALLED and grows with each task; each skill task removes "(planned" markers for its skills from help, README, the CLAUDE.md template and eager rules — cost if wrong: none.
- Ruling R105: extraction/ is deleted only after traces-16 confirms the port (spec, brief §10); Task 15 stops before the delete if no confirmation exists — cost if wrong: the seed stays a little longer.

## Progress
Note: eval sandbox fixed on r2d2 (Marc authorized sudo sysctl kernel.apparmor_restrict_unprivileged_userns=0, until reboot). Doctor smoke eval PASS 1/1, $0.17. Milestone-2 tasks may run one smoke eval per new skill (--runs 1 --ablation none --max-cost-usd 1).
Tasks 1-2: implemented (commits 3efbf97..7ddbe7f), DONE_WITH_CONCERNS
- Ruling R106: generic peeve pools live in agents/editor.md (spec §12), not agents/references/ — files under agents/ subfolders load as broken agents; a test forbids them — plan text superseded — cost if wrong: none.
- Ruling R107: ploma_config.summary gains discipline, slug, style flags, pipeline language, env contract names and gotchas (truncated to keep the summary under 1,500 chars) — agents must get these without a tool call — fix in this unit's round — cost if wrong: longer subagent context.
- Ruling R108: ${CLAUDE_PLUGIN_ROOT} substitution inside agent files is unverified, so session_context --subagent injects a line "ploma scripts: <absolute path to scripts/>" and agents run scripts from that path (falling back to ${CLAUDE_PLUGIN_ROOT}) — deterministic — fix in this round — cost if wrong: one extra context line.
- Ruling R109: claim-verifier attribution comment reworded where the source has em-dashes or the Task context: fork wording — consistent with m1 — cost if wrong: none.
Ruling R110: no plugin evals run without Marc's explicit approval (he questioned the $0.20-per-skill smoke plan); evals are structure-tested with pytest only — cost if wrong: skill-following regressions surface later, in traces-16 testing or a manual eval run.
Tasks 1-2: review needs fixes (3 Important: Bash-less agents told to run scripts (controller-mandated by my resolution); R107; R108) — fix round 1 dispatched, FIX_BASE 7ddbe7f
- Ruling R111 (supersedes my Task 1 resolution): Bash-less agents load venue/discipline by Read on paths injected at subagent start (ploma.d override first, then plugin root); only verifier and claim-verifier run scripts — cost if wrong: none.
- Ruling R108 amended: subagent context injects `ploma root:` and `ploma scripts:` absolute paths.
Tasks 1-2: minor (deferred): verifier names pdfinfo outside the Project context block; report-header example contains a literal page budget
Tasks 1-2: fix round 1/5 (5 addressed, 0 open; commits 7ddbe7f..3ac1310)
Task 1: complete (commits 3efbf97..3ac1310, review clean)
Task 2: complete (commits 3efbf97..3ac1310, review clean)
Tasks 1-2: minor (carry into Task 9): editor quote check uses Grep "fixed string" but Grep takes regex; tell it to escape metacharacters or pick a prefix without them; duplicate step number 4 in editor.md
Tasks 1-2: minor (carry into Task 8): claim-verifier cite_lookup invocation must pass --max <limits.doi_lookups_per_run>; map script statuses (missing/mismatch HIGH, unreachable MED, not_indexed LOW or cannot-verify); matches_claim lists omit not-verifiable-claim-type
Tasks 1-2: minor (deferred): limits.md says the summary shows active values but only three limits appear; multi-line gotchas break one-line layout
Ruling R112: Tasks 3 and 5 dispatched as one unit (three deterministic scripts, separate files) — cost if wrong: larger review surface.
Tasks 3+5: implemented (commits 3ac1310..0245012), DONE_WITH_CONCERNS
- Ruling R113: extra findings abstract_number_only_in_results WARN, metric_key_missing WARN, results_unreadable WARN, and scripts/_texmask.py stand — cost if wrong: none.
- Ruling R114: spec §7.2 governs over my resolution: numbers in the abstract AND the introduction (first \section through the next \section) must appear in the rest of the body, a table, a caption or results; same severities — fix in this unit's round — cost if wrong: more WARN/FAIL on intro numbers that only appear in a figure image.
- Ruling R115: style finding ids include the file: style.<kind>.<relpath>:<line> — fix in this round — cost if wrong: none.
- Ruling R116: integer cells in the FIRST column of a tabular are row labels or ranks and are not checked against results — fix in this round — cost if wrong: a wrong first-column count goes unflagged.
Tasks 3+5: review needs fixes (7 Important: R114, R115, R116 missing; wrapped tables erased; last-digit typos match (partly plan-mandated); en-dash ranges as negatives; placeholder FAIL on macro definitions) — fix round 1 dispatched, FIX_BASE 0245012
- Ruling R117: siunitx \num/\qty/\SI parsed with the right kind; \num and $\pm$ table cells checked — promoted minor — cost if wrong: none.
- Ruling R118: kinds must match for manuscript-vs-manuscript comparisons; a percent may match a results fraction x100 — promoted minor — cost if wrong: none.
- Ruling R119: manuscript-vs-manuscript comparisons use display-rounding equality; tolerance only against results — the spec's tolerance was meant for results, and applying it between two displayed numbers hides last-digit typos — cost if wrong: none.
Tasks 3+5: minor (deferred): numbers defined via \newcommand macros not seen; years 1900-2099 never checked (plan-mandated); tolerances.aggregates ignored; load_results reads every csv/json (may be slow); style: \begin{landscape} flagged as slop, \path/\doi/verbatim not masked, "e.g."/"et al." sentence breaks; begin/end masking fragile
- Ruling R120: \today still flagged in the preamble (it prints via \maketitle); slop ids follow R115 literally (phrase in summary); intro check needs >= 2 \section and ignores \chapter (theses are v0.2) — cost if wrong: none.
Tasks 3+5: fix round 1/5 (8 addressed, 1 open — R119 rounding half-to-even false FAILs; commits 0245012..51536ae)
Tasks 3+5: fix round 2/5 dispatched (Decimal ROUND_HALF_UP), FIX_BASE 51536ae
Tasks 3+5: minor (deferred): \num{1,234}, \num{0.76(2)}, \num{0.76 \pm 0.02} not parsed; mask_definitions masks trailing groups on the same line and misses multi-line bodies; \section inside a body macro counts as a section start
Tasks 3+5: fix round 2/5 (1 addressed, 0 open; commits 51536ae..fa961e5)
Tasks 3+5: fix round 3/5 dispatched (controller probe: "1,234.5" read as count 1,234), FIX_BASE fa961e5
Tasks 3+5: fix round 3/5 (1 addressed, 0 open; commits fa961e5..5cf554d)
Task 3: complete (commits 3ac1310..5cf554d, review clean)
Task 5: complete (commits 3ac1310..5cf554d, review clean)
Tasks 3+5: minor (deferred): no regression tests pinning "1,234,5" and "1,234.5,6" splits
Ruling R121: Tasks 4 and 8 dispatched as one unit (the three validate-stage skills: audit-reproducibility, proofread, verify-claims) — cost if wrong: larger review surface.
Tasks 4+8: implemented (commits 5cf554d..9aca29f), DONE_WITH_CONCERNS
- Ruling R122: proofreader CRITICAL covers visible errors (typos, grammar, broken citations) and counts as HIGH, so proofread WARNs on a paper with typos — matches the sample report's HIGH set — cost if wrong: more proofread WARNs at commit.
- Ruling R123: proofread_summary_<slug>.md is the gate/state artifact; verify-claims records the gate only for manuscript runs; audit-reproducibility asks before adding passport entries (writes and shows the mapping when it cannot ask); eval graders use the "Agent" tool name — cost if wrong: grader mismatch in a future eval run.
Tasks 4+8: review needs fixes (2 Important: verify-claims outcome rule breaks AC5; declined passport write records a false consistency FAIL) — fix round 1 dispatched, FIX_BASE 9aca29f
- Ruling R124: gate entries for proofread/claims only from whole-manuscript runs; DOI cap split across verifier batches; non-falsifiable test fixed; verifier-match to verdict mapping stated — promoted minors — cost if wrong: none.
Tasks 4+8: minor (deferred, note for 0.1.1): a retracted passport claim kept as STALE is a standing consistency FAIL; fine while consistency is recommended, blocks once it becomes required
Tasks 4+8: minor (deferred): proofread replaces per-file reports on re-run (eager rule 5 says extend)
- Ruling R125: the restored outcome rule (0 HIGH and 0 MED is PASS, LOW advisory) lives in cove.md and applies to every CoVe skill — same tiers as traces — cost if wrong: LOW-only lit-review results show PASS with flags rather than PARTIAL.
Tasks 4+8: fix round 1/5 (6 addressed, 0 open; commits 9aca29f..8ad1754)
Task 4: complete (commits 5cf554d..8ad1754, review clean)
Task 8: complete (commits 5cf554d..8ad1754, review clean)
Ruling R126: Tasks 6 and 7 dispatched as one unit (write and format skills) — cost if wrong: larger review surface.
Field test (traces-16, scripts driven directly at 3efbf97 on a scratch copy of the traces repo): onboard all detections correct; doctor READY_WITH_WARNINGS (28 legacy WARNs) then READY after simulated retirement (AC3 reached); compile PASS x3 incl. up-to-date and make -B; validate-bib --semantic PASS (reproduces old PASS). Slash-skill wrappers and interactive install untested (Marc by hand).
- Ruling R127: a field-fix unit (D1-D7) runs right after Tasks 6-7 and before Task 9: D1 escaped DOIs/urls unescaped before lookup (Important, falsification test with \_ Springer DOI); D2 NBSP normalised in evidence; D3 metric_keys recommendation excludes id/threshold/count-like config keys and scans one nesting level, else asks open; D4 onboard proposes document.discipline as a gap (recommend ml for ML-ish venues, else generic); D5 doctor groups legacy WARNs one per kind with the list in Observed; D6 compile report keeps the raw build tail only on FAIL; D7 compile report lists LaTeX warnings (float specifier changes etc.) as INFO. D8 (settings suggestion lists absent linters) left as is — harmless. — cost if wrong: none.
Tasks 6+7: implemented (commits 3efbf97-line..284cdad; base 8ad1754), DONE_WITH_CONCERNS
- Ruling R128: new scripts sections.py, page_map.py, arxiv_rules.py and pdf_pages.heading_positions (reading-order heading search) stand — spec goal 7 (deterministic work in scripts); heading_positions avoids the abstract false match — cost if wrong: none.
- Ruling R129: arxiv_rules' hidden-file check excludes .git*, .gitignore, .gitattributes, .ploma and editor dirs (they are not uploaded) — fix in this unit's round — cost if wrong: none.
- Ruling R130: write's contract test written after the SKILL.md stands (it asserts content the old tree lacked) — cost if wrong: weaker TDD evidence.
Tasks 6+7: review needs fixes (4 Important: merge range swallows end-matter; R129 not applied; heading search matches prose; presubmit exit codes unspecified) — fix round 1 dispatched, FIX_BASE 284cdad
- Ruling R131: merge only in a --merge run (bare yes tells the user the exact rerun command); span comparison ignores trailing blank lines; stale .ploma/tmp/write-* swept; arxiv_rules flags *_suggestion.tex drafts — promoted minors — cost if wrong: none.
Tasks 6+7: minor (deferred): write reads paper_spec.md only with --from-spec (spec §7.1 says whenever present; brief allows); sections.check reads the draft twice
- Ruling R132: an \input of a file without \section stays part of the preceding section (tables, figures); a bare title starting with a single capital or Roman numeral is matched like a numbered heading — cost if wrong: a rare mis-placed page start.
Tasks 6+7: fix round 1/5 (5 addressed, 1 new Important regression: right-column headings in two-column PDFs not found; commits 284cdad..d3e5069)
Tasks 6+7: fix round 2/5 dispatched (column-gap anchor; case-insensitive body only; exit-code wording), FIX_BASE d3e5069
- Ruling R133: a heading followed by a single space and prose is read as prose (real -layout output separates columns with wide gaps); a double-space-then-bare-title false match remains possible, numbered form tried first — cost if wrong: a rare mis-placed page start.
Tasks 6+7: fix round 2/5 (3 addressed, 0 open; commits d3e5069..a17e861)
Task 6: complete (commits 8ad1754..a17e861, review clean)
Task 7: complete (commits 8ad1754..a17e861, review clean)
Field fixes (R127): dispatched, base a17e861
Field fixes: implemented (commits a17e861..326b891)
- Ruling R134: bare `n` counts as a count key (not a metric); escaped-DOI cache entries are looked up once more; discipline recommendation follows the recommended venue, and the onboard skill re-derives it when the user picks another venue — cost if wrong: none.
Field fixes: review needs fixes (2 Important: D3 counts/hyperparameters still recommended; D4 every LNCS paper -> ml, my R127 wording) — fix round 1 dispatched, FIX_BASE 326b891
- Ruling R135 (corrects R127): llncs-conference is not an ML venue; ML venues are springer-ml plus names with learning/neurips/icml/iclr/aaai/ijcai/kdd; the python-pipeline-with-results rule still yields ml; re-derivation never overwrites an explicit choice — cost if wrong: an ML LNCS paper without a pipeline gets generic and the user picks ml.
Field fixes: minor (deferred): _norm_doi also normalises API DOIs (harmless); _metric_keys may read a later unrelated results file without naming it
Field fixes: fix round 1/5 (5 addressed per report; side effect: k/size tokens exclude precision_at_k, effect_size; commits 326b891..f07e143)
- Ruling R136: `k` excluded only as the whole key (or top_k/topk); `size` only in the listed parameter compounds; ranking and effect-size metrics stay — cost if wrong: none.
Field fixes: fix round 2/5 dispatched, re-review will cover rounds 1-2 (FIX_BASE 326b891)
- Ruling R137: the batch token excludes keys like batch_accuracy (rare; user can type it) — cost if wrong: one hand-typed metric key.
Field fixes: fix round 2/5 (all addressed, 0 open; commits 326b891..a799d33). Field fixes: complete (commits a17e861..a799d33, review clean)
Field re-test (traces-16, a799d33): D1 fixed (six partial WARNs gone; 5 remaining are true findings), D2, D4, D6, D7 confirmed; milestone 1 signed off by the peer.
Field fixes: minor (deferred): metric_keys still recommends parameter-like keys such as *_boundary_* and `dependency` (a threshold); the user confirms the list at onboard
Task 9: implemented (commits a799d33..d2a29e2), DONE_WITH_CONCERNS
- Ruling R138: review/devils-advocate record PASS on completion with the decision in extras (a Major verdict must not stall next_stage); cross-artifact uses a nested Skill call to /ploma:audit-reproducibility (field-test it); lens 7's validate_bib writes the bib gate entry (a real semantic run); variance referees alternate domain/methods; stress output stress_gauntlet.md; --peer venue overrides config; editor gains a Novelty claims table — cost if wrong: nested skill call may not run, then the user runs audit-reproducibility separately.
Task 9: review needs fixes (1 Important: adversarial re-audit agent with write tools lacks the data-not-instructions line) — fix round 1 dispatched, FIX_BASE d2a29e2
- Ruling R139: promoted minors: CAP_RE scans SKILL.md; variance N 2..cap (default 3); stress exclusive with r<N> kept; desk-reject respawn fully specified; adversarial round count is per run; fixer limited to .tex/.bib under document.root; recommendation->state token map; referees read only named files; help lists both opt-out flags; default mode falls back to generic-journal and converts .pdf with pdftotext; cross-artifact passes --no-rerun to audit-reproducibility so review never stalls on a background rerun — cost if wrong: none.
Task 9: fix round 1/5 (11 addressed, 0 open; commits d2a29e2..5fff23c)
Task 9: complete (commits a799d33..5fff23c, review clean)
Task 9: minor (deferred): audit-reproducibility help line omits --no-rerun (internal flag); --peer with a .pdf manuscript does not tell agents about the converted text
Task 10: implemented (commits 5fff23c..dab1eca), DONE_WITH_CONCERNS
- Ruling R140: brainstorm's hand-off back from superpowers:brainstorming, grill's one-question-per-turn and lit-review's verified block need an interactive or networked run (field test); missing literature.sources dir is WARN; CHANGELOG is updated once in Task 15 — cost if wrong: none.
Task 10: review needs fixes (2 Important: lit-review VERIFIED heading can hold unchecked papers; brainstorm has no exit from superpowers:brainstorming and conflicts with options-first) — fix round 1 dispatched, FIX_BASE dab1eca
- Ruling R141: promoted minors: lit-review re-run --max and computable verifier cap; existing bib discovered when build.bib_files is empty; grill header Repro and needed-lens-wins; grill eval prompt no longer coaches; spec eval guards and no-AskUserQuestion path; spec names unused decision logs — cost if wrong: none.
Task 10: fix round 1/5 (7 addressed, 0 open; commits dab1eca..0ff05cf)
Task 10: complete (commits 5fff23c..0ff05cf, review clean)
Task 10: minor (deferred): lit-review verifier cap ignores lookups made by --keys re-runs
Task 11: implemented (commits 0ff05cf..28e1ca6), DONE_WITH_CONCERNS
- Ruling R142: rounds are set, not counted, when an event carries `round`: state.record sets rounds[skill] = max(current, round) when extra round is given, increments only when it is absent; respond records round = the referee round being answered (from the report or the previous response), audit runs record mode=audit with no round change — fix in this task's round (state.py plus test) — cost if wrong: none.
- Ruling R143: respond accepts optional `--since <git-ref>` (the submitted version); when given, a location counts as revised only if `git diff <ref> -- <file>` touches it; without it the skill says locations are unverified against the submitted version — fix in this round — cost if wrong: none.
- Ruling R144: Bash(rm -f /tmp/*) cleanup permission stands (a TMPDIR elsewhere only prompts) — cost if wrong: one permission prompt.
Task 11: review needs fixes (5 Important: R142, R143 missing; re-run can overwrite author text; fragile id matching; conversion loses the temp path) — fix round 1 dispatched, FIX_BASE 28e1ca6
- Ruling R145: form blocks take precedence over numbered items in web-form reports; audit-mode wording scoped; cannot-verify-other row; real-format fixture test — promoted minors — cost if wrong: none.
Task 11: minor (deferred): no test of the in-place update path or audit-never-edits (needs a model run)
- Ruling R146: a mode=audit event with no round leaves rounds unchanged (intent of R142); rounds.respond holds the referee round answered — cost if wrong: none.
Task 11: fix round 1/5 (6 addressed, 0 open; commits 28e1ca6..9c52486)
Task 11: complete (commits 0ff05cf..9c52486, review clean)
Task 11: minor (deferred): rounds.review mixes the adversarial run counter with file rounds; stray indent after the audit record code fence
Task 12: implemented (commits 9c52486..ce0ab5c), DONE_WITH_CONCERNS
- Ruling R147: hidden skills' evals use the slash-command prompt and a deterministic grader instead of a Skill-tool grader (test exemption widened from onboard to all disable-model-invocation skills); one learnings rule file, unscoped when mixed; a promote before onboard starts the receipt and onboard keeps the entry; deep-audit's path/restated-fact/dangling checks stay in agents for v0.1 — cost if wrong: deep-audit checks are less deterministic than they could be.
Task 12: review needs fixes (1 Important: deep-audit eval grades a check outside the skill's scope) — fix round 1 dispatched, FIX_BASE ce0ab5c
- Ruling R148: receipt keeps/records only the learnings rule outside rendering; doctor INFO for a demoted learnings rule; learn --promote record failure path; compress-session asks before appending; context monitor tells the model to suggest /ploma:checkpoint; quality_reports README lists checkpoints — promoted minors — cost if wrong: none.
Task 12: fix round 1/5 (7 addressed, 0 open; commits ce0ab5c..6583f35)
Task 12: complete (commits 9c52486..6583f35, review clean)
Task 12: minor (deferred): record_created_once rendered-path check is dead code after the allowlist
Ruling R149: Tasks 13 and 14 dispatched as one unit (commit gate + commit skill; analysis-pipeline template is small) — cost if wrong: larger review surface.
Tasks 13+14: implemented (commits 6583f35..3430667), DONE_WITH_CONCERNS
- Ruling R150: the empty "Milestone 2 (not yet installed): None." help heading and the CLAUDE.md template "Planned: none." line are removed in Task 15 with their tests; the analysis-pipeline project skill is user-owned once written (stays when the pipeline is disabled); GatePrep checks/errors fields, limits rows for commit rounds and override cap, and consistency.run_recorded refactor stand — cost if wrong: none.
Tasks 13+14: review clean (Approved, 0 Critical/Important); FIX_BASE 3430667
- Ruling R151: follow-up hardening of /ploma:commit (outward-facing): override recorded only at commit time; anchored parse_override used via a check-override subcommand; reason passed via heredoc file; allowed-tools narrowed (no gh *, git push *, git checkout *); clean-tree check before prepare; args never count as override; explicit Step 0b continuation; template frontmatter quoting; typed CLI outcomes — reviewer minors promoted — cost if wrong: none.
Tasks 13+14: minor (deferred): fix-and-recheck applies diffs via a permission prompt (no Edit in allowed-tools); test_stale_gate_halts_before_git checks text order only
- Ruling R152: a failed pre-commit hook still consumes the override (no undo command, which the model could misuse) — cost if wrong: an extra override counted after a hook failure; the user can reset the streak by fixing a required check. A user message line exactly 'PLOMA_MESSAGE' truncates check-override input (can only lose text).
Tasks 13+14: fix round 1/5 (R151: 9 addressed; 1 minor regression: cross-line reason; commits 3430667..11ac316)
Tasks 13+14: fix round 2/5 dispatched (same-line reason), FIX_BASE 11ac316
Tasks 13+14: minor (deferred): Step 4 override re-runs gate.check (tree may change between Step 0 and 4); a reason line equal to PLOMA_REASON ends the heredoc early (fails safe)
Tasks 13+14: fix round 2/5 (1 addressed, 0 open; commits 11ac316..0ce91b1) — verified by controller probe (5 cases) plus suite 1155 and validate; no separate re-review for a one-line regex (Ruling R153 — cost if wrong: none, probe covers the finding)
Task 13: complete (commits 6583f35..0ce91b1, review clean)
Task 14: complete (commits 6583f35..0ce91b1, review clean)
- Ruling R154: Task 15 runs without the eval step (R110: Marc has not approved eval spend), without deleting extraction/ (R105: needs traces-16 confirmation after its milestone-2 field test) and without tagging or pushing a release tag (outward-facing; after the final review and Marc's go) — cost if wrong: release waits on two confirmations.
Task 15: implemented (commits 0ce91b1..41e0a28), DONE_WITH_CONCERNS
- Ruling R155: BRIEF.md moved to docs/BRIEF.md (shipped tree no longer names extraction/); tests spell the path as "extraction" + "/" so the grep check stays meaningful — cost if wrong: the spec's "Inputs: BRIEF.md" line points at the old location.
Task 15: review folded into the final whole-branch review (docs-only diff), as in milestone 1
Final review (milestone 2): With fixes — 0 Critical, 7 Important (semantic bib FAIL defeated by structural refresh; nested results pool hides wrong cells; LNCS credits block swallowed by section span; respond round 2 merged into round 1; review --r2 dead end after real reports; right-column heading above left on same page lost; analysis-pipeline template pre-approves all Bash). One fix wave dispatched, FIX_BASE 41e0a28.
- Ruling R156: bib gate entries carry a .bib content hash; commit_gate keeps a semantic FAIL (refreshing freshness only) while the .bib is unchanged and names /ploma:validate-bib --semantic — closes a silent defeat of a required check — cost if wrong: none.
- Ruling R157: with metric_keys set, table cells and intro/abstract numbers match only values under those keys (any depth); unkeyed magnitude matches are INFO placed_by_unkeyed_value and go to audit-reproducibility Phase 2 — cost if wrong: more INFO lines.
- Ruling R158 (corrects R144): temp files are deleted by a script or a prompted rm, not Bash(rm -f /tmp/*).
Final fix wave (m2): implemented (commits 41e0a28..a5e5a7d), DONE_WITH_CONCERNS
- Ruling R159: a results value matches a metric key when any key-path component equals it (avg_fitness.mean counts) — the common mean/std layout must not degrade to INFO — cost if wrong: none.
- Ruling R160: the above-the-previous-hit heading search skips the first two non-empty lines of a page (running heads) — cost if wrong: a heading set in the first two lines of a right column is missed (rare).
- Ruling R161: commit records and stages the state event before git commit (no sha in the event; a failed hook leaves it staged and the skill says so); respond_files.py archive-round and clean-tmp replace shell mv/rm; two old tests pinning replaced behaviour updated — cost if wrong: none.
Final fix wave: round 2 dispatched (R159, R160)
Final fix wave (m2): round 2/2 (R159, R160) done; scoped re-review: 8/8 findings addressed, 1 new Important regression.
Final review: parked — Important: page_map positions ignore the column, so with a right-column heading found above the previous left-column hit the earlier section gets 0.0 pages (scripts/page_map.py:87-90 with pdf_pages hits) — Ruling R162: not fixed in a second wave (process: one final fix wave); surfaced to Marc with the fix (column-aware position: right half maps to page-1 + 0.5 + line/(2*lines), plus a page_map two-column test); affects only two-column PDFs in /ploma:format's page map, not the LNCS traces paper — cost if wrong: misleading cut-plan sizes on two-column venues until fixed.
Final review: minor (deferred): bare-title upward search can match a table header row; respond archives the old document under the new report round number (should use the existing document's Response round); stale semantic PASS silently replaced by structural PASS on .tex edit; pre-fix semantic entries lack bib_sha; \verb not masked; "e.g." counts two words
Milestone 2: complete with one parked Important (R162).

## Milestone 2 field test (traces session, 6a3c7a2, headless skills on scratch copies)
7 of 8 pass. write --merge left the LNCS credits block byte-identical; respond read ids R1/R3/R4 from content and kept a hand-edited response; review --peer produced desk review, two referees and a decision; commit stopped on a standing semantic bib FAIL. extraction/ deletion confirmed by the peer.
- D9 (major): consistency table-cell check cannot detect wrong metric cells (pool of 6613 keyed values within 0.01 covers the displayed value space; a planted 0.12 matched a different record).
- D13 (major): a fabricated reference cannot FAIL because keyless Semantic Scholar returns 429, so all_answered is never true.
- D10 passport claim not marked STALE after the manuscript is fixed; D11 passport_invalid does not name the field; D12 verifiers had Bash denied headless (likely a background-subagent permission artifact); D14 an unresolved DOI on a real work is only partial; peer outputs collide across venues; doctor drift id has a double dot.
- Ruling R163: field-fix unit 2 covers D9, D13, D10, D11, D14, peer dir per venue, drift id, the parked R162 page-map column fix, and the respond archive-round minor; D12 is documented (agent tool use in headless background runs), not changed — cost if wrong: none.
Field fixes 2: implemented (commits 73b3d0a..112511e); review: Critical D9 one-record rule flags correct multi-method tables; Important R162 gutter misreads one-column tables, D10 stale after line shifts, density ignores tolerance, D13 fails real theses — fix round 1 dispatched.
- Ruling R164 (replaces the one-record rule): a table row's label identifies the entity; each cell must match a keyed value located under that entity (path component or string field), preferring keys carrying the column header's distinguishing token (hm vs dfg); cells matching only another entity or another column WARN; unknown labels fall back to per-cell plus density INFO — cost if wrong: tables with unlabelled rows get only the weaker check.
- Ruling R165: theses need all three citation sources answering to be missing; books stay strict — cost if wrong: a fabricated thesis is WARN not_indexed.
- Ruling R166: no billed `claude plugin eval` runs, ever (Marc, relayed by the traces session); testing is pytest plus headless field tests; README and /ploma:help describe evals as optional and unrun; evals/ stays — cost if wrong: none, evals can be run later by choice.
Field fixes 2: fix rounds 1-3 complete (8a777cb..216dfe5); re-review probes clean; residual (parked, Minor): an ambiguous row label such as "Model" against model_a and model_b gets no cross-row check; short team or model codes are a documented gap.
- Ruling R167: extraction/ deleted in one commit; the seed commit b02f494 is tagged `seed` and docs point there — cost if wrong: none, git show seed:extraction/... recovers any file.


## Field re-test 2 (traces session, fd7a1e4)

D9 PASS with gaps (attribution names the file stem, not the entity; a same-entity other-method cell passes), D13 PASS but regression: real grey-literature entries Weijters2006 (tech report typed @Article) and Sivaraman2002 (proceedings, no DOI) FAIL bib.lookup.missing with S2 down, blocking the required bib gate. D10 PASS, D11 PASS.
- Ruling R168: bib.lookup.missing (FAIL) requires a DOI dead on both registries, or no DOI with all three sources answering and no grey-literature markers (tech report, working paper, report, thesis wording in journal/booktitle/institution/type; publisher or organization Citeseer; proceedings without DOI or ISBN); every other absence is not_indexed WARN worded "not found in Crossref or OpenAlex; confirm it exists" — cost if wrong: a fabricated reference with no DOI is a WARN, not a FAIL, when S2 is down or it looks like grey literature.
- Ruling R169: table attribution names the entity by its record's name field when present, cites repo-relative paths, lists matches from the row's own file first, and applies the column-to-key mapping before entity matching; same-entity other-method detection waits on the real table structure from the traces session — cost if wrong: warnings stay hard to act on.
Field fixes 3: implemented (61e8a8a, 901ab82, 2e8942a); review: Important grey-literature words matched as substrings ("Scientific Reports", "Synthesis Lectures"), fixed with whole-word markers; parked Minor: table_method_ambiguous also fires on unrelated numeric tables (INFO only); a section naming two methods takes the first; DOI-less theses are never missing (R168 supersedes R165 for those; a fabricated thesis was already only WARN in the field). Median aggregate rows give table_cell_not_in_results WARN by design.
Field fixes 4: implemented (1337062, 86afe36): table-wide source vote per results directory, pins anywhere before the next tabular, table_source_missing/unused WARNs, not_indexed wording; probes clean, 1284 tests.
