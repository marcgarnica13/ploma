# Pre-submission checks

`/ploma:format --presubmit` runs every check below as parallel Bash calls in one message (no subagents: each check is a deterministic tool), then merges the results by severity into `<outputs.dir>/presubmit_<slug>.md`. A check whose tool is not installed is SKIP with its install hint, never PASS.

## The checks

`<tex files>` is `document.main` and every `.tex` file it inputs (the `sources` of the page map, or Glob `<document.root>/**/*.tex` without `*_suggestion.tex`). Run from the repo root.

| Check | Command | Severity of its findings | Install hint when absent |
|---|---|---|---|
| chktex | `chktex -q -n1 -n8 -n36 -v0 <tex files>` | WARN (one per reported line) | `tlmgr install chktex`, or the `chktex` system package |
| lacheck | `lacheck <document.main>` | WARN (one per reported line) | `tlmgr install lacheck`, or the `lacheck` system package |
| texcount | `texcount -inc -sum -brief <document.main>` | INFO (the word count) | `tlmgr install texcount`, or the `texlive-extra-utils` system package |
| placeholders | `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/placeholders.py" --root . --json` | as printed (FAIL, WARN) | ships with ploma |
| bibliography | `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/bib_check.py" <document.main> --bib <each build.bib_files> --json` | as printed | ships with ploma |
| style | `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/style_check.py" --root . --json` | as printed (WARN, INFO) | ships with ploma |

Then the venue's `submission_checks`, read from the profile:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/profiles.py" --root . --json show <venue.profile>
```

| submission_checks entry | How | Severity |
|---|---|---|
| `placeholders` | the placeholders check above (do not run it twice) | as printed |
| `undefined_refs` | `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/latex_log.py" <build.log> --json`: each undefined citation or reference | FAIL; no log yet: SKIP, "run /ploma:compile first" |
| `page_budget` | the page map's budget line (`scripts/page_map.py`) | over budget FAIL; unverified or no PDF SKIP |
| `anonymization` | only when `document.anonymized` is true; Grep the tex files (see below) | WARN each |
| `arxiv_rules` | `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/arxiv_rules.py" --root . --json` (`\pdfoutput`, figure formats .pdf/.png/.jpg, hidden files, `.bbl` present or `.bib` included, `\today`, comments) | as printed |

An entry not in either table: list it as SKIP, "no automatic check; check by hand".

## Exit codes

Read each command's exit code before its output. Exit 0 means no FAIL, not no findings: a WARN or INFO result also exits 0, and chktex exits 0 even when it prints warnings. A result (findings or none) goes into the merge; a check that did not run is SKIP with the reason, never PASS.

| Command | Clean | Result with findings | Did not run |
|---|---|---|---|
| placeholders.py, bib_check.py, arxiv_rules.py | 0 = no FAIL | 1 = findings (a result) | 2 = did not run |
| style_check.py, latex_log.py, profiles.py | 0 = no FAIL | 1 = findings (a result; latex_log.py: errors in the log) | 2 = did not run |
| chktex | 0, no output | 0 or non-zero with output = findings (a result) | non-zero with no output = did not run |
| lacheck | 0, no output | any output = findings (a result) | |
| texcount | 0 | | non-zero = did not run |
| any | | | 127 = not installed: SKIP with the install hint |

For a script that did not run (exit 2), quote its error message as the SKIP reason.

### Anonymization (judgment on Grep hits)

Look for: an `\author{...}` that is not a placeholder such as "Anonymous", `\thanks{`, an acknowledgments section or paragraph, a personal or institutional URL (a code host user name, a lab page), and self-citations phrased in the first person ("our previous work [n]"). Each hit is a WARN with `file:line` and the verbatim text. No hit: PASS.

## Merging

- Severity order: FAIL, WARN, INFO. A check's own verdict is its worst finding (PASS when it has none). SKIP is not a pass.
- Copy findings verbatim from the tool output: location (`file:line`), the message, and the fix the tool gives or a short one of your own. Never reword a location.
- Long lists (more than 20 findings of one check at one severity): give the first 20 and the count of the rest.
- The overall verdict: FAIL when any FAIL, else WARN when any WARN, else PASS. SKIPs are listed but do not change it; say how many checks did not run.

## Report

Open with the report header (`${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/report-header.md`, title "Pre-submission Checks"). Then:

```markdown
**Verdict:** FAIL | WARN | PASS (N checks run, M skipped)

## Checks

| Check | Tool | Status | Findings |
|---|---|---|---|
| chktex | chktex | WARN | 4 |
| lacheck | lacheck | SKIP | not installed: tlmgr install lacheck, or the lacheck system package |
| arxiv_rules | arxiv_rules.py | WARN | 3 |

## FAIL (N)

1. **placeholders** sections/results.tex:12: "TODO: add the baseline" -> remove the marker or write the text.

## WARN (N)

## INFO (N)

## Not run

- <check>: <why, with the install hint>
```

The report describes the current files only: when one exists, replace it.
