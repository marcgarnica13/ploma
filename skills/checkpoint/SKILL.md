---
name: checkpoint
description: Save a structured state snapshot before stopping or handing off. Captures the active plan, recent decisions, path:line pointers, open questions and the next one to three actions into <outputs.dir>/checkpoints/<date>_<slug>.md, and proposes up to three learnings for the project ledger (appended only after the user's yes). Never touches the manuscript. Use when the user says checkpoint, save state, snapshot before I stop, where am I, wrap up for handoff, or before a long break, a model switch or a collaborator handoff.
argument-hint: "[short-topic-slug] [--no-learn]"
disable-model-invocation: true
allowed-tools: Read, Glob, Grep, Write, Edit, Bash(python3 *), Bash(mkdir *), Bash(git status *), Bash(git log *), Bash(git diff *), Bash(git branch *), Bash(ls *)
---

Plugin root: if your shell lacks CLAUDE_PLUGIN_ROOT, prefix every command below with CLAUDE_PLUGIN_ROOT=<the directory two levels above this SKILL.md> (each shell call is a new process; an export does not carry over).

<!-- Pattern adapted from Hugo Sant'Anna's clo-author v4.2.0 (github.com/hugosantanna/clo-author),
     used with permission. Original /checkpoint shape: project-level session handoff with
     state snapshot + memory updates. This implementation is reimplemented in original
     prose against this template's narrative-session-log + plan-on-disk + auto-memory
     architecture. Attribution credit: Hugo Sant'Anna. -->

# ploma checkpoint

Arguments: `$ARGUMENTS`. The first word that is not a flag is the topic slug. `--no-learn` skips the learnings proposal.

No `ploma.yaml` in the repo root: say "ploma is not set up here. Run /ploma:onboard." and stop.

A checkpoint is the structured, committed record the next session (yours, a collaborator's, or a fresh context after compaction) resumes from in under a minute. The narrative lives in `<outputs.dir>/session_logs/` (gitignored); the checkpoint points to it and never retells it. This skill writes the checkpoint file and, after a yes, ledger lines. It never edits a `.tex`, `.bib` or pipeline file.

## Phase 1: Gather state

1. Resolve the config once and take `outputs.dir` from it:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/ploma_config.py" --json
   ```

2. Read, in this order. A read that finds nothing records "(none on disk)"; never invent content.
   - Latest plan: `ls -t <outputs.dir>/plans/*.md` and take the first. Extract its status (DRAFT, APPROVED, COMPLETED), title, files to modify, and any line starting with "Open questions", "Risks" or "Next".
   - Latest session log: `ls -t <outputs.dir>/session_logs/*.md`, first one. Extract its latest "Next steps" or "Blockers" lines.
   - The ledger `<outputs.dir>/learnings.md`, so you do not propose a learning it already holds.
   - Lifecycle position: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/state.py" next --json` (stage and the next step).
   - Git: `git branch --show-current`, `git log --oneline -20`, `git status --short`, `git diff --stat HEAD`. Capture the branch, the last five subjects and the count of uncommitted files. No git repo: say so in the file.
   - The task list, when one is in flight in this session: the in-progress item and the next pending ones.

## Phase 2: Write the checkpoint

Slug: from the arguments; else from the active plan's file name without its date prefix (and tell the user you derived it); else ask the user for one rather than invent it. Lowercase, kebab-case.

Path: `<outputs.dir>/checkpoints/<YYYY-MM-DD>_<slug>.md` (create the directory with `mkdir -p`). If the file exists, read it and add a dated `## Update <HH:MM>` section rather than overwrite it.

Keep the file under about 80 lines. When the state does not fit, the plan is the right place; the checkpoint is a thin index that points back at it. Template:

```markdown
---
date: YYYY-MM-DD
branch: <current branch, or "(no git)">
plan: <path to the active plan, or "(none)">
session-log: <path to the latest session log, or "(none)">
stage: <stage from state.py>
status: in_progress | paused | ready-to-merge
---

# Checkpoint: <short topic>

## Goal
<one sentence>

## Where I am
<last completed step, current step, what is just not yet done>

## File pointers
- `<path>:<line>`: <what to look at there>
(three to eight, each a real path; check each with Glob or Read before writing it)

## Recent decisions
- <why something was done, not visible from the diff> (skip the section when there are none; do not pad)

## Open questions
- Q1: <question someone picking this up would ask>

## Next actions
1. <imperative, concrete>
2. ...
3. ...

## Resume prompt
> Resuming from checkpoint `<outputs.dir>/checkpoints/<file>`. Read it, then continue with action 1.
```

Next actions are one to three, never more. Trim "Recent decisions" and "Open questions" first when the file runs long.

## Phase 3: Propose learnings (skip with `--no-learn`)

Offer zero to three candidate learnings this session produced, each in the ledger format of `${CLAUDE_PLUGIN_ROOT}/skills/learn/references/ledger-format.md`:

```
1. [LEARN:<topic>] <one line> (<YYYY-MM-DD>)
   Why: <what makes it non-obvious>
```

Skip candidates the ledger already holds and anything `ploma.yaml` already states (engine, bibliography tool, venue, page budget, main file). More than three candidates means the session log is thin: say so and suggest updating the log instead.

Ask which to keep ("all", "none", or numbers). Append only the accepted lines to the end of `<outputs.dir>/learnings.md` (create it from the plugin's `templates/learnings.md` header only when it is missing). No answer, or the session cannot ask: append nothing and list the candidates in the reply.

## Phase 4: Record and report

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/state.py" record checkpoint INFO --artifact <outputs.dir>/checkpoints/<file>
```

Reply:

```
Checkpoint saved: <outputs.dir>/checkpoints/<file>
  Branch: <branch>   Status: <status>   Stage: <stage>
  Active plan: <path or none>   Open questions: <count>
  Learnings appended: <n> (of <m> proposed)
  Resume: paste the file's resume prompt into a fresh session.
```

## When not to use

- The narrative of what happened: the session log.
- A forced distillation before auto-compaction, with an explicit list of what to discard: `/ploma:compress-session`.
- A commit message: `/ploma:commit` writes its own.

No active plan: write a thin checkpoint with `plan: (none)` and suggest writing a plan under `<outputs.dir>/plans/` next time; a checkpoint without a plan is weak.
