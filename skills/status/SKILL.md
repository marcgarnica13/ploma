---
name: status
description: One-screen ploma status for a paper repo. Shows the lifecycle stage and the next recommended stage, the commit gate verdict and what blocks it, the active plan and its status, the newest session log and the context monitor reading. Use when the user asks where things stand, what stage the paper is at, whether it can be committed, or what to do next.
allowed-tools: Read, Glob, Grep, Bash(python3 *)
---

Plugin root: if $CLAUDE_PLUGIN_ROOT/scripts is not a directory, prefix every command below with CLAUDE_PLUGIN_ROOT=<the directory two levels above this SKILL.md> (each shell call is a new process; an export does not carry over).

# ploma status

Read-only. One screen; no advice beyond the next stage.

No `ploma.yaml` in the repo root: say "ploma is not set up here. Run /ploma:onboard." and stop.

Gather, then print one block:

1. Lifecycle:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/state.py" render
   ```

2. Commit gate (exit 1 is a failing verdict, not an error):

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/gate.py" --json check
   ```

   Show one line `gate: <verdict>`, then one line per entry in `reasons` (blocking) and `warnings`, then `override streak: <n>/3`.

3. Outputs directory: `outputs.dir` from `ploma.yaml` (default `quality_reports`).
4. Newest plan: Glob `<outputs.dir>/plans/*.md` (newest first) and Read the first. Show its name and its first `**Status:**` line, or "no plan".
5. Newest session log: Glob `<outputs.dir>/session_logs/*.md`, newest first; show its name, or "no session log".
6. Context monitor: if `.ploma/context-monitor-cache.json` exists, Read it and show one line: tool calls counted this session and the checkpoint nudges already shown. Absent: omit the line.

Layout:

```
stage: <from state.py render>
next:  <from state.py render>
gate:  <verdict>
  - <reason or warning>
  override streak: <n>/3
plan:  <name> (<status>)
log:   <name>
context: <line>
```
