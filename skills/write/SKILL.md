---
name: write
description: Draft or redraft one section of the paper into a sibling <stem>_suggestion.tex file beside the section's file, never into the manuscript. Finds the section by title, label or path, follows the paper spec on request, self-checks the draft (style, numbers and notation against the rest of the paper, on a copy), shows a diff against the current section and lists open flags. Merges over the section only with --merge and the user's explicit yes. Use when the user asks to write, draft, redraft, rewrite, shorten or tighten a section of the paper.
argument-hint: "<section title | sec:label | path> [--from-spec] [--merge]"
allowed-tools: Read, Glob, Grep, Write, Bash(python3 *), AskUserQuestion
---

# ploma write

Arguments: `$ARGUMENTS`. Everything that is not a flag is the section query: a `\section` title (case does not matter), a label such as `sec:intro`, or a `.tex` path under `document.root`. `--from-spec` drafts against `<outputs.dir>/paper_spec.md`. `--merge` applies an existing draft over the section (see Merge). The user's request in the conversation (shorter, a different emphasis, a new paragraph) is the brief for the draft.

No `ploma.yaml` in the repo root: say "ploma is not set up here. Run /ploma:onboard." and stop.

This skill never edits the manuscript unless `--merge` is given and the user says yes. It writes one sibling file and edits only the section in scope. A contradiction with another section is raised as an open flag, never fixed there. The sibling format and the merge rules are in `${CLAUDE_PLUGIN_ROOT}/skills/write/references/sibling-file.md`; read it first.

## 1. Find the section

1. Read the resolved config once:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/ploma_config.py" --json
   ```

2. No query in the arguments: list the sections and ask which one (AskUserQuestion with the titles; without it, ask in text and stop):

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/sections.py" --json list
   ```

3. Resolve the query (quote it as one argument):

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/sections.py" --json resolve "<query>"
   ```

   Exit 2 means no match, several matches, or a path outside `document.root`: quote the message, which names the candidates, and ask the user to pick one. Never guess between two sections.

   The output gives `file`, `start`, `end` (the line range), `label`, `sha`, `sibling` (the draft path), `sibling_exists`, `date`, `spec`, `spec_exists` and `pipeline_enabled`.

4. `--merge` in the arguments: go to Merge below and skip steps 2 to 5.

## 2. Read before drafting

1. The draft already exists (`sibling_exists`): read it first. Ask with AskUserQuestion: "Revise the existing draft" (Recommended: it keeps the earlier work), "Start over", "Only re-check it" (go to step 4). Never overwrite a draft silently.
2. The section: Read `file` with offset `start` and limit `end - start + 1`.
3. Context: the abstract, the introduction, and the sections before and after this one, enough to know the notation, the defined terms, the numbers already reported and what each section promises. Note every symbol and term the section uses that another section defines.
4. Style: `style.sentences`, `style.forbid_em_dash` and `style.forbid_phrases` from the config, and `${CLAUDE_PLUGIN_ROOT}/rules/eager/style.md`.
5. `--from-spec`: when `spec_exists`, read the spec at `spec` and pick the items this section serves (claims with their evidence pointers, the section architecture entry, locked decisions, figures needed). When it is absent, say "paper_spec.md not found at <spec>; drafting without it." and continue.

## 3. Draft

Write the sibling file at `sibling` with the Write tool: the header block from the reference (Source with the line range, Source sha copied from `sha`, Spec items served, Date from `date`, Merge line), one blank line, then the body.

The body replaces the whole section, from its `\section` line to its last line:

- Short, direct scientific sentences. One claim per sentence. Active voice when the actor matters.
- No sentence-level em-dash or en-dash (unless `style.forbid_em_dash` is false). Use a full stop, a comma, a colon or parentheses. Number ranges such as `1--5` are fine.
- None of the forbidden phrases in the style rule or `style.forbid_phrases`. No preamble or closing aimed at the reader of the draft.
- Keep the notation, terms and numbers of the rest of the paper. Every number in the draft comes from the current section, another section, a table, or a results file. Never invent a number, a citation key or a result.
- Keep the section's `\label` and every label another section references.
- Figures: when `pipeline_enabled`, the line before each new `\includegraphics` is `% ploma:source <script> <args>`. When the repo does not show which script makes the figure, ask the user; never invent a script name.

## 4. Self-check

Before showing anything, run both checks in one message (two Bash calls, in parallel):

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/style_check.py" --root . "<sibling>" --json
```

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/sections.py" --json check "<query>" "<sibling>"
```

`style_check.py` reads the style block from `ploma.yaml` and reports em-dashes and filler phrases (WARN) and long sentences (INFO) with `file:line:col`. `sections.py check` copies the manuscript to `.ploma/tmp/`, replaces the section in the copy with the draft body, runs the consistency pass on the copy and on an unspliced copy, deletes both copies and reports:

- `consistency.findings`: each with `change` `new` (caused by the draft) or `unchanged` (already in the paper), with draft lines mapped to the sibling file; `consistency.resolved` lists findings the draft removes.
- `new_numbers_unplaced`: numbers the draft introduces that appear nowhere else in the manuscript or the results files.
- `figures_without_source`: new figures with no `% ploma:source` line (only when the pipeline is enabled).
- `stale`: true when the section changed after the draft header's Source sha.
- `diff`: the current section against the draft body, in `diff -u` format.

The real manuscript files are only read. Never run the consistency pass with `--record` from this skill, and never on a manuscript you have edited for a check.

Fix what the draft itself caused (style findings, `new` consistency findings that are the draft's own mistakes) by rewriting the sibling, then run both checks again. At most the verification retry cap in `${CLAUDE_PLUGIN_ROOT}/rules/eager/limits.md`; what remains after that is reported, not looped on. Never remove a number from the draft just to silence a finding when the user asked for it; flag it instead.

## 5. Show the result

In this order:

1. **Draft:** the sibling path, the section and line range it would replace, and the spec items served (or why none).
2. **Self-check:** the two check outputs summarized. One finding per row, each with the four fields of `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/finding-format.md`:

   | Location | Current | Fix | Severity |
   |---|---|---|---|
   | `sections/intro_suggestion.tex:12` | "<the line, verbatim>" | <the change> | MAJOR |

   Location is the sibling `file:line` from the output. Current is the text at that line, copied from the sibling. Severity: a `new` consistency FAIL is CRITICAL; an em-dash, a filler phrase or a `new` consistency WARN is MAJOR; a long sentence is MINOR. Findings marked `unchanged` were already in the paper: give their count in one line, not the rows. Quote the verdict lines as printed. A check that did not run is never reported as clean: say which one and why.
3. **Diff:** the `diff` field in a `diff` code block, as printed.
4. **Open flags:** found, not fixed. One line each with its location:
   - `stale` true: "The section changed after this draft was written; re-check the diff before merging."
   - each `new_numbers_unplaced` entry: "Number <raw> at <location> is not found in the manuscript or results; give its source or remove it."
   - each `figures_without_source` entry: "<location>: no `% ploma:source` line; which script and arguments make this figure?"
   - contradictions with other sections you noticed (a different count, a symbol defined two ways, a claim the results do not support), each with both locations and the verbatim text of both. Never edit the other section.
   - a label or `\ref` target the body dropped that another section still uses.
5. **Next:** "Reply yes to merge it (/ploma:write <query> --merge), or tell me what to change."

Record the state event (PASS when no open flag and no CRITICAL or MAJOR finding remains, WARN otherwise):

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/state.py" record write <PASS|WARN> --artifact <sibling>
```

## Merge

Only with `--merge`, and only after the user said yes to this draft in this conversation.

1. The sibling does not exist: say "No draft at <sibling>. Run /ploma:write <query> first." and stop.
2. Run the self-check of step 4 on the sibling as it is now. If the user has not yet said yes to its diff in this conversation, show steps 5.2 to 5.4 and ask with AskUserQuestion: "Merge this draft" or "Keep the draft, do not merge". Without AskUserQuestion, ask in text and stop; merge only after a later explicit yes. Silence, "looks good" about something else, or a yes given before a later change to the draft is not a yes to merge.
3. `stale` true: say the section changed after the draft was written, show the new diff and ask again. Never merge a stale draft without a fresh yes.
4. Apply the merge rules in the reference: Read the section's current lines, then one Edit whose `old_string` is exactly those lines and whose `new_string` is the draft body (the sibling without its header). Nothing outside the line range changes.
5. Confirm: run `sections.py --json resolve "<query>"` again; the section now starts with the body's first line and spans the body's length. Then delete the sibling (`rm "<sibling>"`).
6. Record and reply:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/state.py" record write PASS --artifact <file> --extra merged=true
   ```

   Say which lines of which file changed and that the draft was deleted. End with: "Run /ploma:compile to rebuild the PDF."

When the Edit fails (the current text no longer matches), stop and say so; never patch around it.
