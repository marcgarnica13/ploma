---
name: doctor
description: Read-only readiness check for a ploma paper repo. Reports runtime, config, TeX toolchain, manuscript, project files, lifecycle state, dependencies and legacy harness conflicts as PASS, WARN, FAIL, INFO or SKIP, with one verdict (READY, READY_WITH_WARNINGS, NOT_READY). Use when the user asks whether the repo or paper is ready, healthy or set up correctly, why something ploma does is failing, or after onboarding.
argument-hint: "[--json] [path]"
allowed-tools: Read, Glob, Grep, Bash(python3 *)
---

Plugin root: if $CLAUDE_PLUGIN_ROOT/scripts is not a directory, prefix every command below with CLAUDE_PLUGIN_ROOT=<the directory two levels above this SKILL.md> (each shell call is a new process; an export does not carry over).

# ploma doctor

Read-only. Never edits a file, never asks "proceed?", never fixes anything.

1. Run it, passing the arguments through (`$ARGUMENTS`: an optional path, an optional `--json`):

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/doctor.py" "$ARGUMENTS"
   ```

   With both a path and `--json`, pass them as two quoted words: `"--json" "<path>"`.

   Exit 0 is READY or READY_WITH_WARNINGS, exit 1 is NOT_READY (a result, not an error), exit 2 is a usage error or a missing directory: quote the message and stop.

2. Print the output verbatim in a fenced block. Do not summarise or reorder it.

3. Under it, one sentence per FAIL, then one per WARN, in the order printed: what is wrong and its remediation line, as a command where there is one (`/ploma:onboard`, `/ploma:compile`, an install command). INFO and SKIP get no sentence.

4. End with the verdict line: `Verdict: <verdict>`. With no `ploma.yaml`, the first FAIL says to run `/ploma:onboard`; say that and nothing more.
