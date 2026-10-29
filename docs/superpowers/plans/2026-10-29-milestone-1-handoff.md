# ploma milestone 1: hand-off to traces-16 for real-TeX testing

> `extraction/` was removed from the tree after the milestone-2 field test (R105). Paths under `extraction/` below refer to the `seed` tag: `git show seed:extraction/<path>`.

Milestone 1 is on `main` (see `git log`; the ledger commit is 90f7bd2). The peer session was offline when this was written, so the hand-off lives here.

## Install (HTTPS path, since SSH to GitHub hangs on the paper host)

```
gh auth setup-git
export CLAUDE_CODE_PLUGIN_PREFER_HTTPS=1
/plugin marketplace add marcgarnica13/ploma
/plugin install ploma@ploma
```

Then restart the session or run `/reload-plugins`.

## What is installed

`/ploma:onboard`, `/ploma:doctor`, `/ploma:status`, `/ploma:help`, `/ploma:compile`, `/ploma:validate-bib`, the hooks (session context, pre-compact, context monitor, verify reminder, log reminder) and the eager rules. Everything else is milestone 2 and is marked planned in help.

## Test sequence on the traces paper

1. `/ploma:onboard --dry-run`, then `/ploma:onboard`. Expected: main `manuscript/samplepaper.tex`, class llncs, make in `manuscript/`, bibtex, `mybib.bib`, `review/`, a pipeline under `src` with `src/results`. The venue gap recommends `llncs-conference` with `springer-ml` offered (pick springer-ml). The page-budget question recommends 12 and asks whether references count. With the legacy harness still present, onboard prints a retirement checklist (skill name conflicts, hook entries in `.claude/settings.json`, statusline, rules restating build facts) and deletes nothing.
2. `/ploma:doctor`. Expected READY after retiring the legacy harness and compiling; READY_WITH_WARNINGS with legacy WARNs before. Paste the full render.
3. `/ploma:compile` twice (the second run should PASS "build was up to date"), then `/ploma:compile --clean` (runs `make -B`). Paste `quality_reports/compile_samplepaper.md`.
4. `/ploma:validate-bib --semantic`. `@misc` and `@techreport` entries that no index holds should be WARN not_indexed, not FAIL. Paste `quality_reports/bib_audit_semantic.md` and compare it with the old PASS report.

## Open questions only the paper host can answer

- Do the sensitive API keys reach the script? Semantic Scholar 429s in the report suggest they do not; lookups still work without keys.
- Does `claude plugin eval` run there? Its sandbox needs `socat`, which r2d2 lacks. The smoke command is in the README.

Report defects as a list with the script output pasted. Every ruling made during execution and every deferred minor is in `2026-10-29-ploma-foundation-ledger.md` next to this file. `extraction/` stays until milestone 2 is ported and traces-16 confirms.
