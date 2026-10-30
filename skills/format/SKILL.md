---
name: format
description: Check the built PDF against the page budget with a per-section page map, and when the paper is over budget draft a cut plan ordered by value per page (proposals only, nothing is cut). With --presubmit, run the pre-submission checks in parallel (chktex, lacheck, texcount, placeholders, bibliography, style and the venue's submission checks such as the arXiv source rules) and merge them by severity into one report. Use when the user asks about page count, page budget or page limit, where the pages go, what to cut, or for a pre-submission or arXiv readiness check.
argument-hint: "[--budget N] [--presubmit]"
allowed-tools: Read, Glob, Grep, Write, Bash(python3 *), Bash(chktex *), Bash(lacheck *), Bash(texcount *)
---

Plugin root: if $CLAUDE_PLUGIN_ROOT/scripts is not a directory, prefix every command below with CLAUDE_PLUGIN_ROOT=<the directory two levels above this SKILL.md> (each shell call is a new process; an export does not carry over).

# ploma format

Arguments: `$ARGUMENTS`. `--budget N` replaces `venue.page_budget` for this run. `--presubmit` adds the pre-submission checks.

No `ploma.yaml` in the repo root: say "ploma is not set up here. Run /ploma:onboard." and stop.

This skill never edits a source file. The cut plan proposes; the user decides what to cut and applies it (for one section, `/ploma:write <section>` drafts the shorter version as a sibling file). It records no commit gate entry.

## 1. Page map

1. Read the resolved config once:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/ploma_config.py" --json
   ```

2. Map the PDF (add `--budget N` only when the arguments contain it):

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/page_map.py" --json
   ```

   Exit 0 is within budget or no budget, exit 1 is over budget (a result, not an error), exit 2 is no PDF, an unreadable PDF or config: quote the message. With no PDF, say "No PDF yet. Run /ploma:compile first." and stop, unless `--presubmit` was given: then continue with section 3 and mark `page_budget` SKIP.

The script finds each `\section` of the manuscript in the PDF text in reading order (as "<number> <title>", then by the bare title), the page where the references start (same rule as `/ploma:compile`), the estimated pages per section, and the figure, table and word counts per section. It needs `pdftotext` (poppler) for the section pages; without it, quote `sections_method` and its install hint, and give the total only.

Quote the budget line as the script reports it (`status`, `counted` of `budget`, `over_by`, `note`). `stale` true: say "The PDF is older than the sources; the map reflects the last build. Run /ploma:compile for a current map." A section with `start_page` null was not found in the PDF text: show "not found", never a guessed page.

## 2. Budget report and cut plan

Write `<outputs.dir>/page_budget_<slug>.md` in the format of `${CLAUDE_PLUGIN_ROOT}/skills/format/references/cut-plan.md`. Read that reference first. When one exists, read it first, then replace it: it describes the current PDF.

- Within budget (or no budget): the header, the measured table, the page map and the one-line verdict. No cut plan.
- Budget unverified (references excluded and their start not found): the header, the page map and the reason; ask the user for the page where the references start, or to install poppler, and stop there.
- Over budget: the full cut plan. Before ranking cuts, Read each section the plan touches (its `file` and `line` from the map) to judge what is contribution and what is detail. Order the cuts by pages recovered per unit of content lost, give each a page estimate built from the map (`est_pages`, figure and table counts, words), and make the cuts add up to the overage or say that they do not. Name what is not cut, the risk and a recommendation. Every number is the script's or is marked `~` as an estimate.

## 3. Pre-submission (only with `--presubmit`)

Follow `${CLAUDE_PLUGIN_ROOT}/skills/format/references/presubmit.md`. Read it first.

1. Read the venue profile's `submission_checks` (`profiles.py ... show <venue.profile>`) and the list of `.tex` files.
2. Run every check as a separate Bash call, all in one message so they run in parallel: chktex, lacheck, texcount, `placeholders.py`, `bib_check.py`, `style_check.py`, and for the submission checks `latex_log.py` (undefined_refs) and `arxiv_rules.py` (when `arxiv_rules` is listed). `page_budget` reuses the page map of section 1; anonymization is the Grep pass the reference describes, only when `document.anonymized` is true. No subagents: these are deterministic tools.
3. Read each exit code with the reference's Exit codes table: it says which codes are a result (findings) and which mean the check did not run. In short: the ploma scripts exit 1 for findings and 2 when they did not run; chktex exits non-zero with output for findings; any lacheck output is findings; texcount non-zero did not run; 127 is not installed, SKIP with the install hint. Never report a check that did not run as clean.
4. Merge by severity into `<outputs.dir>/presubmit_<slug>.md` in the reference's format: the verdict line, the checks table, then FAIL, WARN and INFO findings, each with its location, the verbatim message and the fix, then the checks not run.

## 4. Record

Status: FAIL when the page budget is over or a pre-submission check failed; WARN when only warnings remain or the budget is unverified; PASS otherwise. The artifact is the pre-submission report with `--presubmit`, else the page budget report.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/state.py" record format <PASS|WARN|FAIL> --artifact <report path>
```

Format is not a commit gate check: do not call `gate.py`.

## Reply

1. The budget line as printed, and the page map table (section, start page, estimated pages, figures).
2. Over budget: the cut plan's headline (pages to recover, the top three cuts with their page estimates) and the report path. Within budget: one line.
3. With `--presubmit`: the verdict line, the checks table, the FAIL findings one line each (location, message, fix), the count of WARN and INFO, and the checks not run with their install hints. Then the report path.

End with one line, the first that applies:

- no PDF: "Run /ploma:compile first, then /ploma:format."
- pre-submission FAIL: "Fix the FAIL findings above, then run /ploma:format --presubmit again."
- over budget: "Pick the cuts to apply; /ploma:write <section> drafts a shorter section as a sibling file."
- PDF stale: "Run /ploma:compile, then /ploma:format for a current map."
- otherwise: "Within budget. Run /ploma:format --presubmit before submitting." (or, after a clean `--presubmit`, "Ready for the final checks: /ploma:validate-bib --semantic and /ploma:proofread.")
