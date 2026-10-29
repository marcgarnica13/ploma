# Learnings

The project learnings ledger. /ploma:learn appends one line per learning; /ploma:checkpoint and
/ploma:compress-session propose entries and append them only after your yes. `/ploma:learn --promote`
proposes the durable ones as rule text for `.claude/rules/ploma-learnings.md`, writes only on approval,
and marks the ledger lines it promoted.

Entry format, one line each, appended at the end of this file:

[LEARN:<topic>] <one line: what to do, and why if not obvious> (<YYYY-MM-DD>)

A promoted entry gains a suffix: [LEARN:<topic>] <one line> (<YYYY-MM-DD>) (promoted <YYYY-MM-DD>)

<topic> is one lowercase word or kebab-case phrase (build, bib, figures, pipeline, review). Edit or
delete lines by hand when they go stale.

## Entries

