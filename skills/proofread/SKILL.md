---
name: proofread
description: Report-only proofreading of the manuscript's .tex files for grammar, typos, overflow, terminology and notation consistency, and academic quality, with terminology drawn from the config style block and the discipline card. Runs one proofreader agent per file, writes one report per file plus a summary, and records the proofread entry of the commit gate. Never edits; fixes are applied only after the user approves them. Use when the user asks to proofread, copy-edit, check for typos or grammar, or before submission.
argument-hint: "[file.tex | all]"
allowed-tools: Read, Glob, Grep, Write, Agent, Bash(python3 *)
---

Plugin root: if your shell lacks CLAUDE_PLUGIN_ROOT, prefix every command below with CLAUDE_PLUGIN_ROOT=<the directory two levels above this SKILL.md> (each shell call is a new process; an export does not carry over).

# ploma proofread

Arguments: `$ARGUMENTS`. A `.tex` path reviews that file only. Empty or `all` reviews every `.tex` file under `document.root`.

No `ploma.yaml` in the repo root: say "ploma is not set up here. Run /ploma:onboard." and stop.

This skill never edits a source file. It produces reports; the user decides what to apply (Phase 3). The protocol is `${CLAUDE_PLUGIN_ROOT}/rules/reference/proofreading-protocol.md`: Propose, Approve, Apply.

## Phase 1: Propose

1. Read the resolved config once:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/ploma_config.py" --json
   ```

2. Files. Glob `<document.root>/**/*.tex`. Put `document.main` first, then the others in path order. Leave out `*_suggestion.tex` drafts and anything under a build or output directory. A file named in the arguments replaces the list (it must exist; otherwise say so and stop).
3. Terminology and style for the agents: `style.sentences`, `style.forbid_em_dash`, `style.forbid_phrases`, `venue.cite_style`, and the discipline key (`document.discipline`, `generic` when unset). The agent reads the discipline card's `method_conventions` and the shipped style rule itself.
4. Spawn one `ploma:proofreader` agent per file (Agent tool, `subagent_type: ploma:proofreader`), all in one message so they run in parallel. Each prompt holds: the file to review, the full file list (so terms defined in another file count), `build.log` when the file exists, and the terminology block from step 3. Do not paste file contents; the agent reads them.
5. Each agent returns findings with location, verbatim current text, fix, category and severity. Map severity: CRITICAL is HIGH, MAJOR is MEDIUM, MINOR is LOW. Drop a finding whose quoted text is not in the file (check with Grep, fixed string; escape regex metacharacters or search a prefix without them) and count the drops. An agent that errors or returns no findings table: say which file was not proofread; that file is missing from the gate count, and the summary says so.

## Write the reports

One report per file at `<outputs.dir>/<stem>_report.md` (`<stem>` is the file name without `.tex`; when two files share a stem, prefix the parent directory: `<dir>_<stem>_report.md`). A proofreading report describes the current file only: if one exists, read it first, note its HIGH count for comparison, then replace it.

Each report opens with the header in `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/report-header.md` (title "Proofreading Report"), adds one line on the build (the overfull count from `build.log`, or "no build log"), and states "No source files edited; report only." Then:

```markdown
## HIGH severity (N)

1. **TYPO** sections/intro.tex:51: "<current text, verbatim>" -> "<fix>".
2. **GRAMMAR** sections/intro.tex:68: "<current>" -> "<fix>".

## MEDIUM severity (N)

## LOW severity (N)

## Counts

- HIGH N, MEDIUM N, LOW N. Overfull boxes: N. Dropped (quote not found): N.
- Most impactful before submission: <one or two lines>.
```

Number findings across the whole report so the user can approve them by number. Category is one of GRAMMAR, TYPO, OVERFLOW, CONSISTENCY, QUALITY. A finding that spans files (a term spelt two ways) lists every location.

Then a summary at `<outputs.dir>/proofread_summary_<slug>.md` with the same header: one row per file (report path, HIGH, MEDIUM, LOW), the totals, files not proofread, and the most critical findings across files.

## Record

`open_high` is the total HIGH count across all reports. Status PASS when it is 0, otherwise WARN. The gate entry is recorded only when the run covered the whole manuscript (every `.tex` file under `document.root`, all proofread). A partial run (a file argument, or a file whose agent failed) records only the state event and says so in the reply: "Partial run: proofread gate entry not recorded."

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/gate.py" record proofread <PASS|WARN> --artifact <outputs.dir>/proofread_summary_<slug>.md --extra open_high=<N>
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/state.py" record proofread <PASS|WARN> --artifact <outputs.dir>/proofread_summary_<slug>.md
```

`proofread` is a recommended gate check: a WARN never blocks a commit.

## Reply

Per file: the issue count and the breakdown by severity and category. Then the HIGH findings, one line each (location, current, fix), and the gate entry recorded. End with one line, the first that applies:

- HIGH findings: "Reply with the finding numbers to apply (for example 'HIGH in intro'), or fix them yourself and run /ploma:proofread again."
- no HIGH: "No HIGH findings. Run /ploma:verify-claims next, or name findings to apply."

## Phase 2: Approve

Nothing is applied in the same turn as the report. Applying fixes needs an explicit request from the user after the report, naming the findings (by number, severity or file) or "all".

## Phase 3: Apply

Only after that request, and only the approved findings:

1. For each finding, Read the line, then Edit it with the fix. One edit per finding; `replace_all` only for a finding that names every instance of the same term.
2. Confirm each edit (Grep for the new text). A finding whose current text is no longer there is skipped and reported, never forced.
3. Report what was applied and what was skipped. Then recommend `/ploma:compile`, and `/ploma:proofread` again to refresh the gate entry.
