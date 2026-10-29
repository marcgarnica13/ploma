---
name: compress-session
description: Distil the current conversation into a structured note (active state, decisions with reasons, files touched with path:line, open questions, next one to three actions, what was discarded as noise, proposed learnings) and save it to <outputs.dir>/session_logs/<date>_compression_<topic>.md before auto-compaction. Differs from /ploma:checkpoint (an explicit stop-point snapshot) and from auto-compaction (which truncates rather than distils). Use when context is near the auto-compact threshold, a long run has piled up decisions and dead ends, or the user says compress, distil this session, or structured handoff before context resets.
argument-hint: "[optional-topic-slug]"
disable-model-invocation: true
allowed-tools: Read, Glob, Grep, Write, Edit, AskUserQuestion, Bash(python3 *), Bash(mkdir *), Bash(git status *), Bash(git log *), Bash(git branch *), Bash(ls *)
---

# ploma compress-session: distil, do not truncate

Arguments: `$ARGUMENTS`, an optional topic slug.

No `ploma.yaml` in the repo root: say "ploma is not set up here. Run /ploma:onboard." and stop.

Auto-compaction is lossy: it keeps recent turns and drops earlier ones with no record of what was decided. This skill writes the distilled record instead, so the next context resumes from decisions rather than from a transcript. Long contexts fail in four ways (Drew Breunig, "How Long Contexts Fail", 2025): poisoning (an early wrong statement gets quoted later), distraction, confusion (contradicted facts pile up) and clash (several plans without reconciliation). The "Discarded as noise" section defends against poisoning; the decisions list defends against confusion and clash.

## Compared with /ploma:checkpoint

| | `/ploma:checkpoint` | `/ploma:compress-session` |
|---|---|---|
| When | a natural pause, handoff, model switch | context fatigue, near auto-compaction |
| Keeps | plan, decisions, pointers, next actions | the same plus an explicit "discarded as noise" list |
| Output | `<outputs.dir>/checkpoints/` (committed) | `<outputs.dir>/session_logs/` (gitignored) |
| Learnings | optional proposal | always proposed |

The context monitor hook's nudge and the pre-compact snapshot in `.ploma/` remind you; neither runs this skill for you, because the user reviews the proposed learnings.

## Step 1: Identify the session

Resolve the config once (`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/ploma_config.py" --json`) and take `outputs.dir`. Read the latest session log under `<outputs.dir>/session_logs/` (`ls -t`, first one) and `.ploma/pre-compact-state.json` when it exists. None: the current conversation is the source. Read the latest plan under `<outputs.dir>/plans/` and the ledger `<outputs.dir>/learnings.md` (to avoid proposing duplicates).

## Step 2: Distil

```markdown
# Session compression: <YYYY-MM-DD> <topic-slug>

**Source:** <session log path or "current conversation">
**Context at compression:** <approximate percent, or "unknown">
**Why now:** <approaching auto-compact | mid-plan handoff | accumulated noise | user request>

## Active state
- **Plan:** <path under <outputs.dir>/plans/ or "no active plan">
- **Branch:** <git branch>
- **Last commit:** <sha and subject>
- **Working tree:** <clean | N modified files>

## Decisions made (this session)
1. <decision>. **Why:** <one sentence>. **Where recorded:** <path:line, plan, or "only here">.

## Files touched
- `<path>:<line>`: <what changed, one sentence>

## Open questions
- <question>. **Blocker:** yes or no. **Resume at:** <pointer>.

## Next actions
1. <specific next step with a path>
(one to three only)

## Discarded as noise
- <hypothesis, approach or dead end>: <why it did not work>

## Proposed learnings
- [LEARN:<topic>] <one line> (<YYYY-MM-DD>). **Evidence:** <pointer>.
```

Learning lines follow `${CLAUDE_PLUGIN_ROOT}/skills/learn/references/ledger-format.md`. Leave out anything `ploma.yaml` already states.

Do not paste the conversation. Distillation is the point.

## Step 3: Save

Write `<outputs.dir>/session_logs/<YYYY-MM-DD>_compression_<topic>.md` (`mkdir -p` the directory). Topic: the argument, else the active plan's name without its date, else a two or three word kebab-case summary. The directory is gitignored by onboard: session state, not the committed record (that is `/ploma:checkpoint`).

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/state.py" record compress-session INFO --artifact <outputs.dir>/session_logs/<file>
```

## Step 4: Summarise

Reply with the saved path; the counts of decisions, files touched, open questions and next actions; and the proposed learnings. When there are proposed learnings, ask once with AskUserQuestion which to append to the ledger (all, none, or a choice of them; none first when any looks doubtful). Append only the accepted lines to the end of `<outputs.dir>/learnings.md`. No answer, or AskUserQuestion is unavailable: append nothing and say the user can add them later with `/ploma:learn`. Nothing is merged automatically.

## Anti-patterns

- Running it as a routine replacement for `/ploma:checkpoint`. Checkpoints are cheap and frequent; compressions are for forced moments.
- A "Discarded as noise" list that keeps growing: the same dead end in three compressions in a row means the confusion is structural. Fix the plan or the docs.
- Editing any file other than the compression note (and, after a yes, the ledger).
