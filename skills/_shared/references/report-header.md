# Report header

Every report a ploma skill writes under `<outputs.dir>/` opens with this header, before any other content:

```markdown
# <Report title>: <document title or file name>

**Date:** YYYY-MM-DD
**File:** <path of the file or directory reviewed, relative to the repo root>
**Skill:** /ploma:<skill name> <arguments as given>
**Config:** <one-line config summary>
```

## Fields

- **Title:** the report kind and its subject, for example "Proofreading Report: main.tex".
- **Date:** today, ISO format.
- **File:** what was examined. Several files: the main one, then "and N inputs".
- **Skill:** the slash command and arguments that produced the report, so a reader can re-run it.
- **Config:** one line from the resolved config: venue profile key, discipline (or `generic`), page budget (or `none`), `anonymized` or `not anonymized`, and `pipeline on` or `pipeline off`. Read the values through `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/ploma_config.py" --json`; never restate them from memory. Example: `venue generic-conference; discipline generic; page budget 8; anonymized; pipeline on`.

## Rules

- Filenames use `document.slug`: `<outputs.dir>/<slug>_<report kind>.md`, or the path the skill names.
- If a report already exists at that path, read it first and extend it with a dated section rather than overwrite it, unless the skill says otherwise.
- Findings in the body follow `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/finding-format.md`.
