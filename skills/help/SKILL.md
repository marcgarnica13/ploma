---
name: help
description: What ploma is, which lifecycle stage owns which skill, which ploma skills are installed now and which are planned, and how to install or update the plugin. Use when the user asks for ploma help, what ploma can do, which command to run for a stage, or how to install or update ploma.
argument-hint: "[question]"
allowed-tools: Read, Glob, Bash(python3 *)
---

# ploma help

Answer the user's question (`$ARGUMENTS`) from this page. With no question, give the short tour below. This is a router, not a manual: point to the skill, do not explain its internals.

ploma is a Claude Code plugin for writing, validating, reviewing and formatting LaTeX academic papers. A repo declares its facts once in `ploma.yaml`, and every skill, hook and rule reads them from there.

When a `ploma.yaml` exists, add the recommended next stage:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/state.py" next
```

Without one, the next step is `/ploma:onboard`.

## Lifecycle

| # | Stage | Skill |
|---|---|---|
| 0 | Install | `/ploma:onboard` |
| 0b | Health | `/ploma:doctor` |
| 1 | Brainstorm | `/ploma:brainstorm` |
| 1b | Literature | `/ploma:lit-review` |
| 2 | Grill | `/ploma:grill` |
| 3 | Spec | `/ploma:spec` |
| 4 | Write | `/ploma:write <section>` |
| 5 | Compile | `/ploma:compile` |
| 5b | Format | `/ploma:format` |
| 6 | Validate | `/ploma:validate-bib`, `/ploma:verify-claims`, `/ploma:audit-reproducibility`, `/ploma:proofread` |
| 7 | Review | `/ploma:review`, `/ploma:devils-advocate` |
| 8 | Respond | `/ploma:respond <report>` |
| 9 | Ship | `/ploma:commit` |
| any | Session | `/ploma:status`, `/ploma:checkpoint`, `/ploma:compress-session`, `/ploma:learn`, `/ploma:deep-audit`, `/ploma:help` |

## Installed now

- `/ploma:onboard [--dry-run] [--yes]`: detect the repo's facts, propose `ploma.yaml` and project files, write after approval.
- `/ploma:doctor [path]`: read-only readiness check with a verdict.
- `/ploma:status`: stage, gate, plan, session log, on one screen.
- `/ploma:compile [--clean]`: build the PDF, triage the log, check pages against the budget.
- `/ploma:validate-bib [--semantic] [--skip-doi]`: structural bibliography check; `--semantic` verifies entries against citation APIs.
- `/ploma:audit-reproducibility [--rerun]`: match the paper's reported numbers against the pipeline's results within the configured tolerances and keep the claims passport (needs `pipeline.enabled`).
- `/ploma:verify-claims [file] [--source <path-or-url>]`: fact-check citation and other factual claims with a fresh-context verifier (Chain-of-Verification).
- `/ploma:proofread [file.tex | all]`: report-only proofreading, one report per file; fixes only after approval.
- `/ploma:write <section> [--from-spec] [--merge]`: draft a section into a `<stem>_suggestion.tex` sibling with a self-check and a diff; merges only on `--merge` and your yes.
- `/ploma:format [--budget N] [--presubmit]`: page map per section against the budget, a cut plan when over (proposals only), and the pre-submission checks.
- `/ploma:review [path] [--adversarial | --peer <venue> [--r2|--r3|--stress|--variance N] [--no-novelty-check] | --seven-pass] [--no-cross-artifact]`: a referee-style review; `--peer` simulates the venue's editor and two blind referees, `--adversarial` loops critic and fixer with your approval, `--seven-pass` runs seven lenses.
- `/ploma:devils-advocate [path]`: 5 to 7 skeptical challenges to the paper's design choices; report only.
- `/ploma:brainstorm <topic> [--no-verify]`: 3 to 5 research questions with hypotheses, methods and pitfalls (runs superpowers brainstorming first when enabled); fact-checked.
- `/ploma:lit-review <topic> [--no-verify]`: literature search and synthesis; BibTeX entries offered only after a citation lookup, never written to your bibliography.
- `/ploma:grill [topic or file]`: one question per turn with a recommended answer until no design decision is open; writes a decision log.
- `/ploma:spec [topic | start fresh] [--no-verify]`: the binding paper spec (claims with evidence, venue constraints, section page targets, decisions); edits an existing spec section by section.
- `/ploma:respond <report-path-or-dir> [revised-manuscript] [--since <git-ref>] [--audit <draft>] [--no-verify]`: point-by-point response to referee reports in any format (reviewer numbers read from the content), every concern classified, location claims fact-checked; `--audit` checks an existing draft.
- `/ploma:checkpoint [slug] [--no-learn]`: save a structured snapshot (plan, decisions, path:line pointers, open questions, next actions) under `<outputs.dir>/checkpoints/`; learnings reach the ledger only after your yes.
- `/ploma:compress-session [slug]`: distil the session into a note under `<outputs.dir>/session_logs/` before auto-compaction, with what was discarded as noise.
- `/ploma:learn [note | --promote [entry] | --skill <name>]`: append a learning to the ledger; `--promote` writes approved entries to `.claude/rules/ploma-learnings.md`; `--skill` drafts a project skill after approval.
- `/ploma:deep-audit [--report-only]`: audit the ploma installation (config drift, rule and CLAUDE.md paths, restated config facts, dangling report references, manuscript consistency) with four parallel agents; fixes only after approval, never the manuscript.
- `/ploma:help`: this page.

## Milestone 2 (not yet installed, don't invoke)

commit.

If the user asks for one of these, say it is not installed yet and name the nearest installed skill, if any (`/ploma:doctor` or `/ploma:status` for state, `/ploma:review` for feedback on the paper). Until `/ploma:commit` arrives, `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/gate.py" check` shows whether the required checks have passed.

## Install and update

```
gh auth login && gh auth setup-git
export CLAUDE_CODE_PLUGIN_PREFER_HTTPS=1
/plugin marketplace add marcgarnica13/ploma
/plugin install ploma@ploma
/ploma:onboard
```

Update: `/plugin marketplace update ploma`, then `/reload-plugins`.
