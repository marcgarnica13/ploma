---
name: compile
description: Build the paper's PDF with the repo's own build command (or latexmk), triage the LaTeX log, check pages against the venue budget, and record the compile entry of the commit gate. Reports errors with file and line, undefined citations and references, overfull boxes and the page count. Use when the user asks to compile, build or typeset the paper, to check that it builds, or after editing .tex files.
argument-hint: "[--clean]"
allowed-tools: Read, Glob, Grep, Bash(python3 *), AskUserQuestion
---

# ploma compile

Arguments: `$ARGUMENTS`. `--clean` forces a full rebuild: a `make` build command runs as `make -B` (make rebuilds every target), any other build runs `latexmk -c` first.

No `ploma.yaml` in the repo root: say "ploma is not set up here. Run /ploma:onboard." and stop.

This skill never edits the manuscript. It proposes fixes; the user applies them.

## 1. Build

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/compile.py"
```

Add `--clean` to the command only when the arguments contain `--clean`. Pass nothing else from the arguments.

Exit 0 is PASS, exit 1 is FAIL (a result, not an error), exit 2 is a usage error or an unreadable `ploma.yaml`: quote the message and stop.

The script prints a short summary and the report path (`<outputs.dir>/compile_<slug>.md`). It has already recorded the gate entry and the state event. Do not record them again.

## 2. Report

Read the report file. Quote its `**Status:**` line and its Pages vs budget line. Then, in this order, only the parts that are not empty:

- **Errors.** Quote the first error only, with its file and line, as the report gives it. Say: "Fix the first error, not the last: later errors often follow from it." Read a few lines around that line of that file (Read with offset) and propose one concrete fix as a short diff. Do not list the remaining errors one by one; give their count.
- **Build tool not found or timed out.** Quote the line from the Build section and stop. Say how to fix it (install the tool, or set `build.command` in `ploma.yaml`).
- **Undefined.** List the undefined citation keys and the undefined reference labels.
- **Overfull.** One line with the count above the threshold; name the worst box and its width.
- **Rerun WARN.** One line: build again before submitting.
- **Budget unchecked.** When the Pages vs budget line says the page budget could not be checked, quote it and point to /ploma:format; it is not a failure.

## 3. Rebuild, at most twice

A rebuild happens only after the user approves a proposed fix and says it is applied. Ask once with `AskUserQuestion` (options: "Fix applied, rebuild" (Recommended), "Stop here"). Without `AskUserQuestion`, stop after step 2.

On approval, run step 1 again (without `--clean`) and repeat step 2. At most two rebuilds per invocation. After the second rebuild, report what remains and stop; do not offer a third.

## 4. Next step

End with one line, the first that applies:

- errors remain: "Fix `<file>:<line>` and run /ploma:compile."
- undefined citations: "Run /ploma:validate-bib to find the missing or misspelt keys."
- undefined references (no errors): "Check the \label and \ref names, then run /ploma:compile."
- over the page budget: "Run /ploma:format for the page map and a cut plan."
- PASS: "Compile is clean. Run /ploma:validate-bib next."
