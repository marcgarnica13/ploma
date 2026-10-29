---
name: commit
description: Stage, commit, push, open a PR, and merge to main. Use ONLY on explicit commit intent — user says "commit", "ship it", "push this", "open a PR", "merge to main", "let's commit this", or prefixes with `/commit`. Do NOT auto-invoke on vague end-of-task phrases ("we're done", "wrap up") — those require explicit confirmation first. Runs the standard commit-PR-merge cycle; never force-pushes or skips hooks.
argument-hint: "[optional: commit message]"
allowed-tools: ["Bash", "Read", "Glob", "Task"]
---

# Commit, PR, and Merge

Stage changes, verify quality gates, commit with a descriptive message, create a PR, and merge to main.

## Steps

### Step 0: Quality Gate (Pre-Commit)

**Run before branching.** For every changed `.tex` (proposal) file that has quality rubrics (see [`.claude/rules/quality-gates.md`](../../rules/quality-gates.md)), assess it against the rubric:

- For `proposal/*.tex`: ensure it still builds via `cd proposal && make all` and the log is clean, then apply the quality-gates rubric. (There is no code in this repo — it is writing-only.)

- If any file scores below **80**, halt and report the findings. The user must either fix the issues or explicitly override with phrases like *"commit anyway"* or *"skip quality gate"*.
- If all files score 80+, continue.

Spawn the **doc-verifier** agent (via `Task` with `subagent_type=doc-verifier`) to run compilation/render checks on the changed files. Report pass/fail before committing.

### Step 0b: Surface-Sync Check (Pre-Commit)

**When the commit touches `.claude/` inventory** (adds/removes a skill, agent, rule, or hook), verify that any count claims or "All Skills / All Agents" listings (in `CLAUDE.md`, `.claude/WORKFLOW_QUICK_REF.md`, or `.claude/MEMORY.md`) still match the on-disk counts of `.claude/{skills,agents,rules,hooks}`. If they drift, fix the stale listing before committing. (See `audit-pet-peeves.md` peeves #7 and #18 for why this class of drift matters.)

### Step 1: Check current state

```bash
git status
git diff --stat
git log --oneline -5
```

### Step 2: Create a branch

```bash
git checkout -b <short-descriptive-branch-name>
```

### Step 3: Stage files

Add specific files (never use `git add -A`):

```bash
git add <file1> <file2> ...
```

Do NOT stage `.claude/settings.local.json` or any files containing secrets.

### Step 4: Commit with a descriptive message

If `$ARGUMENTS` is provided, use it as the commit message. Otherwise, analyze the staged changes and write a message that explains *why*, not just *what*.

```bash
git commit -m "$(cat <<'EOF'
<commit message here>
EOF
)"
```

### Step 5: Push and create PR

```bash
git push -u origin <branch-name>
gh pr create --title "<short title>" --body "$(cat <<'EOF'
## Summary
<1-3 bullet points>

## Test plan
<checklist>

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

### Step 6: Merge and clean up

```bash
gh pr merge <pr-number> --merge --delete-branch
git checkout main
git pull
```

### Step 7: Report

Report the PR URL and what was merged.

## Important

- **Never skip Step 0.** Quality gates catch broken compilation, bad citations, and page-limit overflows before they reach `main`. If the user insists on skipping, record their override reason in the commit message.
- Always create a NEW branch — never commit directly to main.
- Exclude `settings.local.json` and sensitive files from staging.
- Use `--merge` (not `--squash` or `--rebase`) unless asked otherwise.
- If the commit message from `$ARGUMENTS` is provided, use it exactly.
