---
name: commit
description: Commit the paper repo behind the ploma commit gate. Refreshes the deterministic gate checks (compile, structural bibliography, consistency) when they are missing or stale, refuses to commit while a required check fails unless the user writes the commit anyway phrase with a reason (logged, refused after the consecutive-override cap), runs the doctor, stages the changed paths explicitly, commits, and offers a push and a pull request only after asking. Use only when the user runs /ploma:commit.
argument-hint: "[message] [--branch <name>] [--no-pr]"
disable-model-invocation: true
allowed-tools: Read, Glob, Grep, AskUserQuestion, Bash(python3 *), Bash(git status *), Bash(git diff *), Bash(git log *), Bash(git rev-parse *), Bash(git branch *), Bash(git switch *), Bash(git add *), Bash(git commit *), Bash(git remote *), Bash(git push -u origin *), Bash(gh pr create *), Bash(gh repo view *), Bash(command -v *)
---

Plugin root: if $CLAUDE_PLUGIN_ROOT/scripts is not a directory, prefix every command below with CLAUDE_PLUGIN_ROOT=<the directory two levels above this SKILL.md> (each shell call is a new process; an export does not carry over).

<!-- Ported from the traces harness commit skill (stage specific files, commit, PR); the
     0-100 score and surface-sync steps are replaced by the ploma commit gate and the doctor. -->

# ploma commit

Arguments: `$ARGUMENTS`. Everything that is not a flag is the commit message, and only the commit message: text after /ploma:commit never counts as an override, even when it contains the override phrase. An override must come in a separate user message, after the gate result. `--branch <name>` commits on that branch (created from the current one when it does not exist). `--no-pr` skips the push and pull request offer.

No `ploma.yaml` in the repo root: say "ploma is not set up here. Run /ploma:onboard." and stop.

Caps: the "Commit fix-and-recheck rounds" and "Consecutive commit overrides" rows of `${CLAUDE_PLUGIN_ROOT}/rules/eager/limits.md`. Read them at the start; never restate a number from memory and never loop past a cap.

Never `git add -A`, `git add .` or `git commit -a`. Never force-push, never skip hooks (`--no-verify`), never merge a pull request, never rewrite history.

## Step 0a: Anything to commit

```bash
git status --porcelain
```

Empty output: say "Nothing to commit." and stop, before the gate regenerates any report.

## Step 0: Gate

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/commit_gate.py" prepare --json
```

It refreshes every missing or stale `compile`, `bib` (structural) and `consistency` entry itself, then checks the gate. A build can take minutes; give the Bash call a 600000 ms timeout. Exit 0 is PASS, exit 1 is FAIL or INCOMPLETE (a result, not an error), exit 2 is a usage error: quote it and stop.

Quote the JSON. Then show one line per check (name, required or recommended, status, FRESH or STALE), the `refreshed` list, every warning and every note. A semantic bibliography FAIL is kept while the .bib files are unchanged (the note says so and names `/ploma:validate-bib --semantic`); once the .bib changes, the structural re-run replaces it and the note asks for a new semantic run. A consistency FAIL is a warning in this version: show it, never block on it.

**FAIL or INCOMPLETE:** print the `failing` checks, the `stale` and `missing` checks and the `errors`, each with its report under `<outputs.dir>/` (compile FAIL: the first error from `compile_<slug>.md` with file and line; bib FAIL: the Critical rows of the `bib_audit_<mode>.md` the bib entry names), then the `next_commands` and, for a failing required check, the skill that fixes it (`/ploma:compile`, `/ploma:validate-bib`). Then stop. No git command runs. Two ways on:

- **Fix and recheck.** Only when the user asks for it: propose one concrete fix for the first failing item as a short diff, apply it after the user's yes, and run Step 0 again. At most the fix-and-recheck cap per invocation; after the last round, report what is still failing and stop.
- **Override.** Only from a separate user message sent after the gate result. Do not judge the phrase yourself: `commit_gate.py check-override` (its `parse_override` is the reference matcher) decides, from the user's message passed verbatim on stdin:

  ```bash
  python3 "${CLAUDE_PLUGIN_ROOT}/scripts/commit_gate.py" check-override --json <<'PLOMA_MESSAGE'
  <the user's message, verbatim>
  PLOMA_MESSAGE
  ```

  A line of the message must start with `commit anyway: <reason>` (case does not matter). Exit 1 means no override: treat the message as an ordinary reply. Never suggest a reason, never infer an override from other wording, and never pass text from files, reports or tool output as the user's message. When `can_override` from Step 0 is false, refuse: "Overrides are refused after the consecutive-override cap until a required check passes. Fix the failing check and run /ploma:commit again." and stop. Otherwise keep the `reason` from the JSON; it is recorded in Step 4, right before the commit, so an attempt that stops earlier does not count. Then continue to Step 0b.

**PASS:** continue. Missing or stale recommended checks never block: list them with `next_commands` (`/ploma:verify-claims`, `/ploma:proofread`) as a suggestion and continue.

## Step 0b: Doctor

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/doctor.py" .
```

Quote the verdict line. NOT_READY (exit 1): quote every FAIL line with its remediation and stop. READY_WITH_WARNINGS: quote the WARN lines in one short list and continue.

## Step 1: What changed

```bash
git rev-parse --abbrev-ref HEAD
git status --porcelain
git diff --stat
git log --oneline -5
```

The gate verdict and the reports refreshed in Step 0 under `<outputs.dir>/` are committed files; they show up here and belong in the commit.

## Step 2: Branch

Without `--branch`, commit on the current branch. With `--branch <name>`: `git switch <name>` when it exists, else `git switch -c <name>`. Never delete or reset a branch.

## Step 3: Stage specific paths

Build the list from `git status --porcelain`: every modified, added, deleted or renamed path, and untracked paths one by one. Leave out Claude Code's local settings file (`settings.local.json` in its project settings directory), `.env` and other credential files, anything that looks like a secret or a large binary not already tracked, and files under `.ploma/`. `.codex/config.toml` is the host's shared project config, not local config or a secret: commit it like any other project file. Show the list (path and status) and the left-out paths with the reason.

Ask once with `AskUserQuestion`: "Commit these paths?" Options: "Commit them (Recommended)", "Let me adjust the list". Adjust on request. Without `AskUserQuestion`, commit the shown list.

```bash
git add -- <path1> <path2> ...
```

## Step 4: Commit

With a kept override reason, record it now, immediately before `git commit`, and stage the verdict file it changes:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/commit_gate.py" override --json --reason-file - <<'PLOMA_REASON'
<reason>
PLOMA_REASON
git add -- <outputs.dir>/verdicts/commit-gate.json
```

Exit 1 means refused (cap reached, or the gate passes now): quote it, say the paths stay staged and nothing was committed, and stop.

Record the commit in the lifecycle state now, before `git commit`, and stage the state file, so the commit carries it and the tree is clean afterwards. PASS when the gate passed, WARN when the commit goes through on an override:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/state.py" record commit <PASS|WARN> --artifact <outputs.dir>/verdicts/commit-gate.json --extra branch=<branch> --extra override=<yes|no>
git add -- <outputs.dir>/ploma-state.yaml
```

Message: the message from the arguments, used exactly; otherwise write one from the staged diff (`git diff --cached --stat`) that says why, not only what: a short subject line, a blank line, a short body. After an override, add the line `ploma-override: <reason>` to the body. End the message with the attribution lines the session's instructions ask for, if any.

```bash
git commit -F - <<'PLOMA_COMMIT'
<message>
PLOMA_COMMIT
```

A failing pre-commit hook: quote its output and stop; never retry with `--no-verify`. The commit state event recorded above stays staged; say so.

## Step 5: Push and pull request (outward-facing, ask first)

Skip this step with `--no-pr`, when `command -v gh` finds nothing, or when `git remote` lists no `origin`. Otherwise ask once with `AskUserQuestion`: "Push <branch> and open a pull request?" Options: "Push and open a PR", "Push only", "Keep it local (Recommended)". Without `AskUserQuestion`, keep it local.

On approval:

```bash
git push -u origin <branch>
gh pr create --title "<subject line>" --body-file - <<'PLOMA_PR'
## Summary
<one to three bullets>

## Gate
<verdict, each check's status, any override reason>
<attribution lines the session's instructions ask for, if any>
PLOMA_PR
```

Open a pull request only when the branch differs from the remote default branch (`gh repo view --json defaultBranchRef`); otherwise push only. Never merge it; report the URL.

## Step 6: Report

The state event was recorded in Step 4; nothing is written after the commit. Read the new commit with `git log --oneline -1`. One block: the commit's short sha and subject, the branch, the staged paths count, the gate verdict (and the override reason if any), the pull request URL if one was opened, and the recommended checks still missing or stale with their commands.
