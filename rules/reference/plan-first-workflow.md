# Plan-first workflow

For any non-trivial task, plan before editing.

## Protocol

1. Read the ledger `<outputs.dir>/learnings.md` for entries relevant to the task.
2. For a vague or large task (several valid readings, more than three files, more than an hour), clarify first: ask at most three to five questions, each with a recommended answer, then write a short requirements note under `<outputs.dir>/specs/` marking each item MUST, SHOULD or MAY and each aspect CLEAR, ASSUMED or BLOCKED.
3. Draft the plan: what changes, which files, in what order, how it will be verified.
4. Save it to `<outputs.dir>/plans/YYYY-MM-DD_short-description.md`. When superpowers is installed, `superpowers:writing-plans` produces it.
5. Present it and wait for approval.
6. Start the session log (see the session-logging rule).
7. Implement, checking off each `- [ ]` item as it lands.

Skip step 2 for a clear, specific, single-file task.

## Plan file format

The first lines name the status on its own line, exactly one of:

```
**Status:** DRAFT
**Status:** APPROVED
**Status:** COMPLETED
```

Then the approach, the files to change, and the verification steps as a `- [ ]` checklist. The pre-compact hook reads the status line and the first unchecked item; keep both accurate.

## Context survival

Before auto-compaction, make sure the plan and the session log on disk are current and open questions are written down. `/ploma:checkpoint` does this in one step.

After compaction or in a new session:

1. Read the newest plan under `<outputs.dir>/plans/`.
2. Check `git log --oneline -10` and `git diff`.
3. State the current task and the next step before continuing.
