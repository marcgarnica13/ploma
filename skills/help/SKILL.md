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
- `/ploma:compile`: build the PDF, triage the log, check pages against the budget.
- `/ploma:validate-bib [--semantic]`: structural bibliography check; `--semantic` verifies entries against citation APIs.
- `/ploma:help`: this page.

## Milestone 2 (not yet installed, don't invoke)

brainstorm, lit-review, grill, spec, write, format, verify-claims, audit-reproducibility, proofread, review, devils-advocate, respond, commit, checkpoint, compress-session, learn, deep-audit.

If the user asks for one of these, say it is not installed yet and name the nearest installed skill, if any (`/ploma:doctor` or `/ploma:status` for state, `/ploma:compile` before any review). Until `/ploma:commit` arrives, `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/gate.py" check` shows whether the required checks have passed.

## Install and update

```
gh auth login && gh auth setup-git
export CLAUDE_CODE_PLUGIN_PREFER_HTTPS=1
/plugin marketplace add marcgarnica13/ploma
/plugin install ploma@ploma
/ploma:onboard
```

Update: `/plugin marketplace update ploma`, then `/reload-plugins`.
