---
name: help
description: What ploma is, which lifecycle stage owns which skill, which ploma skills are installed, and how to install or update the plugin. Use when the user asks for ploma help, what ploma can do, which command to run for a stage, or how to install or update ploma.
argument-hint: "[question]"
allowed-tools: Read, Glob, Bash(python3 *)
---

Plugin root: if your shell lacks CLAUDE_PLUGIN_ROOT, prefix every command below with CLAUDE_PLUGIN_ROOT=<the directory two levels above this SKILL.md> (each shell call is a new process; an export does not carry over).

# ploma help

Answer the user's question (`$ARGUMENTS`) from this page. With no question, give the short tour below. This is a router, not a manual: point to the skill, do not explain its internals.

ploma is a plugin for Claude Code and Codex for writing, validating, reviewing and formatting LaTeX academic papers. A repo declares its facts once in `ploma.yaml`, and every skill, hook and rule reads them from there.

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
- `/ploma:review [path] [--adversarial | --peer <venue> [--r2|--r3|--stress|--variance N] [--no-novelty-check] | --seven-pass] [--no-cross-artifact]`: a referee-style review; `--peer` simulates the venue's editor and two blind referees, `--adversarial` loops critic and fixer with your approval, `--seven-pass` runs seven lenses. `--r<N>` continues a simulated `--peer` review only; for real referee reports use `/ploma:respond` (or `/ploma:respond --audit <draft>` to check your own reply).
- `/ploma:devils-advocate [path]`: 5 to 7 skeptical challenges to the paper's design choices; report only.
- `/ploma:brainstorm <topic> [--no-verify]`: 3 to 5 research questions with hypotheses, methods and pitfalls (runs superpowers brainstorming first when enabled); fact-checked.
- `/ploma:lit-review <topic> [--no-verify]`: literature search and synthesis; BibTeX entries offered only after a citation lookup, never written to your bibliography.
- `/ploma:grill [topic or file]`: one question per turn with a recommended answer until no design decision is open; writes a decision log.
- `/ploma:spec [topic | start fresh] [--no-verify]`: the binding paper spec (claims with evidence, venue constraints, section page targets, decisions); edits an existing spec section by section.
- `/ploma:respond <report-path-or-dir> [revised-manuscript] [--since <git-ref>] [--audit <draft>] [--no-verify]`: point-by-point response to referee reports in any format (reviewer numbers read from the content), every concern classified, location claims fact-checked; `--audit` checks an existing draft.
- `/ploma:checkpoint [slug] [--no-learn]`: save a structured snapshot (plan, decisions, path:line pointers, open questions, next actions) under `<outputs.dir>/checkpoints/`; learnings reach the ledger only after your yes.
- `/ploma:compress-session [slug]`: distil the session into a note under `<outputs.dir>/session_logs/` before auto-compaction, with what was discarded as noise.
- `/ploma:learn [note | --promote [entry] | --skill <name>]`: append a learning to the ledger; `--promote` writes approved entries to the host's learnings target; `--skill` drafts a project skill after approval.
- `/ploma:deep-audit [--report-only]`: audit the ploma installation (config drift, paths in the host's rules and instructions file, restated config facts, dangling report references, manuscript consistency) with four parallel agents; fixes only after approval, never the manuscript.
- `/ploma:commit [message] [--branch <name>] [--no-pr]`: commit behind the gate; refreshes compile, the structural bibliography check and consistency when stale, stops on a required FAIL unless you write `commit anyway: <reason>`, stages paths explicitly, asks before any push or pull request.
- `/ploma:help`: this page.

Every lifecycle skill is installed. `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/gate.py" check` shows whether the required checks have passed without committing.

## Install and update

Claude Code:

```
gh auth login && gh auth setup-git
export CLAUDE_CODE_PLUGIN_PREFER_HTTPS=1
/plugin marketplace add marcgarnica13/ploma
/plugin install ploma@ploma
/ploma:onboard
```

On a host without SSH keys for GitHub, the first two lines set up HTTPS; with SSH keys, skip them.

Update: `/plugin marketplace update ploma`, then `/reload-plugins`.

Codex:

```
codex plugin marketplace add marcgarnica13/ploma
codex plugin add ploma@ploma
```

Then open /hooks in Codex and trust ploma's hooks, and run `$ploma:onboard`. Update: `codex plugin marketplace upgrade ploma`, then reinstall with `codex plugin add ploma@ploma`. On Codex every skill is typed `$ploma:<name>` where this page says `/ploma:<name>`.

## Switching hosts

ploma runs on one host at a time. To move a repo to the other host, run onboard again there. The old host's files are left in place. The doctor reports `host_mismatch` until you do.

## Testing

ploma is tested with `python3 -m pytest -q` and headless field tests (`claude -p --plugin-dir <ploma>` in a real paper repo). The `evals/` cases are optional and bill model calls; the maintainers do not run them.
