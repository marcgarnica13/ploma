---
name: onboard
description: Set up ploma in a LaTeX paper repo. Reads the repo, asks only what it cannot detect, proposes ploma.yaml and the project files, writes them after approval, then runs the doctor. Re-running it on an onboarded repo is an absorption run that never clobbers hand edits. Use when the user asks to install, set up, onboard or re-onboard ploma in a paper repository.
argument-hint: "[--dry-run] [--yes]"
disable-model-invocation: true
allowed-tools: Read, Glob, Grep, Bash(python3 *), Write, Edit, AskUserQuestion
---

# ploma onboard

Arguments: `$ARGUMENTS`. `--dry-run` stops after the proposal and writes nothing. `--yes` skips the single approval question.

Work in the repo root (the current directory). Every script call below is part of the audit record: quote its JSON or text output in a fenced block, under the step it belongs to, in the reply the user reads. Short direct sentences. At every fork, offer options with the recommended one first.

If `AskUserQuestion` is unavailable (a non-interactive session), take each gap's recommended answer, mark it "assumed" in the proposal, and write nothing unless `--yes` was given.

## 1. Refuse or route

- No `.tex` file in the repo (Glob `**/*.tex`): stop with "ploma v0.1 supports LaTeX papers only." Write nothing.
- `ploma.yaml` exists: this is an absorption run. Read it. If `document.type` is set and is not `paper`, stop with "document.type `<type>` is not supported in ploma v0.1; only `paper` is." Otherwise follow the absorption rules at the end of this file alongside steps 2 to 8.
- Neither: a first onboard. Continue.

## 2. Inventory (read-only)

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/inventory.py" --json
```

Quote the JSON. Everything it answers is settled: never ask about it again.

## 3. Main file, only when ambiguous

If `main` is null and `main_candidates` is empty (only fragment `.tex` files), stop. Say: "ploma found no compilable main file (a .tex with \documentclass and \begin{document})." List the `.tex` files found, up to 10, and ask the user to name the main file in their reply. Do not offer to leave it unset. When they name it, continue with the `--main` re-run below.

If `main` is null and there are candidates, ask the `document.main` question alone first, with one `AskUserQuestion` call. Get it from:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/inventory.py" --json gaps
```

Put the gap's `recommended` candidate first, marked "(Recommended)". Then re-run the inventory with the answer and use this output from now on:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/inventory.py" --json --main <answer>
```

Pass the same `--main <answer>` to every later `inventory.py` call.

## 4. Remaining gaps

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/inventory.py" --json gaps
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/inventory.py" propose
```

Quote both. Ask every remaining gap in one `AskUserQuestion` call, up to four questions. Turn each gap into a question as `${CLAUDE_PLUGIN_ROOT}/skills/onboard/references/questions.md` says: recommended option first, each question readable on its own. More than four gaps: ask the first four, then one more call for the rest. No gaps: skip the call.

Apply the answers to the proposed YAML from `propose`. That YAML plus the answers is the proposal.

## 5. Legacy harness

If the inventory's `legacy_harness` list is non-empty, print it as a retirement checklist, one line per item: `path`, then `consequence`. Then say: "onboard deletes and moves nothing; retire these by hand. The doctor reports them as WARN until they are gone." While any item has kind `hook_entry`, withhold the settings suggestion in step 6 and say why: the old hooks would fire alongside ploma's.

## 6. Propose

Show, in this order:

1. The full proposed `ploma.yaml` as a YAML block.
2. The plan table, from the proposal (nothing is written; the proposal goes on stdin):

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/project_files.py" --config - --json plan <<'PLOMA_YAML'
   <the proposed ploma.yaml>
   PLOMA_YAML
   ```

   Quote the JSON, then render a table with columns path, mode, action. Under it, show the `diff` of every `overwrite`, `merge` and `remove` row (a generated rule that will be removed is shown before approval).

   With `pipeline.enabled: true` the plan has a row for `.claude/skills/analysis-pipeline/SKILL.md` (created-once): a project skill for running and extending the pipeline, rendered from the `pipeline` block (language, run directory, rerun command, outputs, metric keys, env contract, gotchas, and the stage chain from the optional `pipeline.stages` list). Say in one line what it is and that it is written once and then belongs to the user. When `pipeline.stages` is unset, the skill says the stage chain is not declared; offer to add the ordered stage names to the proposal.
3. The settings suggestion, unless step 5 withheld it:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/project_files.py" --config - --json settings <<'PLOMA_YAML'
   <the proposed ploma.yaml>
   PLOMA_YAML
   ```

   Show it as a JSON block for `.claude/settings.json` and say: "plugins cannot grant permissions; add this yourself if you want it." Never write it.

`--dry-run`: stop here. Say "dry run: nothing written." and name the next step (`/ploma:onboard` without `--dry-run`).

Otherwise ask once with `AskUserQuestion`: "Write ploma.yaml and the project files listed above?" Options: "Write them (Recommended)", "Stop without writing". With `--yes`, skip the question. Anything but approval: stop, nothing written.

## 7. Write

1. Write `ploma.yaml` at the repo root with the Write tool, exactly the YAML shown in step 6 (absorption run: Edit only, never Write; see Absorption).
2. Apply the project files:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/project_files.py" --json apply
   ```

   Quote the JSON. Rows with `"written": true` were written; the receipt goes to `<outputs.dir>/ploma-receipt.json`. A non-zero exit: quote the error and stop.

## 8. Verify

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/doctor.py"
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/state.py" next
```

Quote the doctor's first two lines (verdict and counts) and every FAIL and WARN line with its remediation. End with:

- `Verdict: <READY | READY_WITH_WARNINGS | NOT_READY>`, and when it is not READY, exactly why in one sentence per FAIL.
- `Next: /ploma:<stage>` from `state.py next`.

## Absorption run (ploma.yaml exists)

- Run every `inventory.py` call with `--main <document.main from ploma.yaml>`.
- Compare `propose` with the current `ploma.yaml`, key by key. Show a short table: key, ploma.yaml, detected. A key present in `ploma.yaml` is the user's: never change it, even when detection differs. Only keys missing from `ploma.yaml` may be added.
- Ask only the gaps whose key is missing from `ploma.yaml`. A key present with null (for example `venue.page_budget: null`) is a deliberate answer: never re-ask it.
- Plan from the current file plus the additions. With no additions, run `project_files.py --json plan` without `--config`.
- Step 7: add the missing keys with Edit, keeping comments and order. Never rewrite `ploma.yaml` with Write. No additions and no plan rows other than `unchanged`: say "nothing to absorb", skip step 7 and go to step 8.
- The plan never overwrites hand-edited files: rows marked `skip_hand_edited` are reported, not written.
