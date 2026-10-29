# Sibling file: header and merge rules

`/ploma:write` never drafts into the manuscript. It writes a sibling file next to the file that holds the section, and the user decides what reaches the paper.

## Path

`<dir of the file holding the section>/<stem>_suggestion.tex`, as `scripts/sections.py resolve` prints it:

- The section is the only `\section` in its own file (for example `sections/intro.tex`): `<stem>` is that file's stem, so the draft is `sections/intro_suggestion.tex`.
- The section sits inside a larger file (for example `main.tex`): `<stem>` is a slug of the section title (lower case, words joined by `_`, at most 40 characters), so the draft is `related_work_suggestion.tex` beside `main.tex`.
- A file with no `\section` (a fragment under `document.root`) is drafted whole: `<stem>` is the file's stem.

`*_suggestion.tex` files are never `\input` by the paper, are left out of the commit gate's manuscript fingerprint, and are skipped by `/ploma:proofread`.

## Header

The draft opens with a block of comment lines, then one blank line, then the body. Every header line starts with `%`. The header ends at the first line that does not.

```latex
% ploma:write draft. Not part of the paper until merged.
% Source: sections/intro.tex lines 1-7 (\section{Introduction}, sec:intro)
% Source sha: 3f9c1a2b7d40
% Spec items served: C1 (identity sentence), C2 (main claim, evidence pointer results/metrics.json)
% Date: 2026-10-29
% Merge: /ploma:write sec:intro --merge replaces lines 1-7 of sections/intro.tex with the body below.
%
```

- **Source**: the file and line range from `sections.py resolve`, the section title and its label (when it has one).
- **Source sha**: the `sha` field from `sections.py resolve`, copied exactly. `sections.py check` compares it with the current section and reports `stale` when the section changed after the draft was written.
- **Spec items served**: with `--from-spec` and `<outputs.dir>/paper_spec.md` present, the identifiers or headings of the spec items the draft serves, each with a few words. With `--from-spec` and no spec file: `none (paper_spec.md not found)`. Without `--from-spec`: `none (not requested)`.
- **Date**: today, ISO format (the `date` field from `sections.py resolve`).
- **Merge**: the exact command and the line range it would replace.

## Body

- The body replaces the whole section span, so it starts with the `\section{...}` line and keeps the section's `\label` unchanged, unless the user asked to rename it.
- Keep every `\label`, `\ref` and `\cite` key that other parts of the paper use. A label removed from the body breaks references elsewhere; raise it as an open flag instead.
- New figures: when `pipeline.enabled`, the line before each new `\includegraphics` is `% ploma:source <script> <args>`, the script and arguments that regenerate the figure. Ask the user for the script when the repo does not answer it; never invent one.
- No notes to the user inside the body. Questions and doubts go in the reply as open flags, not as LaTeX comments.

## Merge rules

A merge happens only in a run invoked with `--merge`, and only after the user says yes in that run to the shown diff. A "yes" after a run without `--merge` is answered with the command to rerun: `/ploma:write <query> --merge`.

1. Run `sections.py resolve` again and `sections.py check` on the draft. If `stale` is true, the section changed after the draft was written: say so, show the new diff, and ask again. Never merge a stale draft without a fresh yes.
2. Read the section's current lines (Read with offset and limit on the range) and the draft body.
3. Replace exactly that line range with the body (everything after the header) using one Edit: `old_string` is the current section text, `new_string` is the body. Nothing outside the range changes.
4. Confirm with `sections.py resolve` and a Read of the new span: it equals the body, ignoring trailing blank lines.
5. Delete the sibling file (`rm <sibling>`), then recommend `/ploma:compile`.

When the Edit fails (the old text is no longer there), stop and say so. Never patch around it.
