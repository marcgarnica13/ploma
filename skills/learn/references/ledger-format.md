# Learnings ledger format

The ledger is `<outputs.dir>/learnings.md` (created by /ploma:onboard from the plugin's
`templates/learnings.md`; its header states this same format). One ledger per project; no other
memory file.

## Entry line

```
[LEARN:<topic>] <one line> (<YYYY-MM-DD>)
```

- `<topic>`: one lowercase word or kebab-case phrase naming the area: `build`, `bib`, `figures`,
  `pipeline`, `review`, `writing`, `tooling`. Reuse a topic already in the ledger before inventing one.
- `<one line>`: what to do next time, in the imperative, plus the reason when it is not obvious.
  Under about 200 characters. No line breaks. Name a path when the learning applies to specific
  files (that is what makes it path-scoped at promotion).
- `<YYYY-MM-DD>`: the day the entry was written.
- Entries are appended at the end of the file, under `## Entries`. Never reorder or rewrite another
  entry; to correct one, append a new entry and delete the stale line by hand.

Pattern (one entry per line):

```
^\[LEARN:[a-z0-9][a-z0-9-]*\] .+ \(\d{4}-\d{2}-\d{2}\)( \(promoted \d{4}-\d{2}-\d{2}\))?$
```

## Promoted entries

`/ploma:learn --promote` appends ` (promoted <YYYY-MM-DD>)` to each entry whose rule text it wrote
into the host's learnings target (`.claude/rules/ploma-learnings.md` on Claude Code, the learnings
block in `AGENTS.md` on Codex). An entry without that suffix is unpromoted. The entry text
itself never changes, so the ledger stays the audit trail.

```
[LEARN:bib] Keep citation keys stable once cited; renaming breaks every \cite (2026-10-12) (promoted 2026-10-29)
```

## What does not go in the ledger

- Facts `ploma.yaml` holds: engine, bibliography tool, venue, page budget, main file. Change the
  config instead.
- Secrets, tokens, personal paths outside the repo.
- Session narrative. That belongs in the session log or a checkpoint.

## The ladder

Route a learning to the cheapest place that works:

1. A check a script or hook can make: say so and suggest the check instead of a ledger line.
2. The ledger (default landing place): `/ploma:learn <note>`.
3. The host's learnings target: only through `/ploma:learn --promote`, with
   approval, for a learning that keeps being missed although it is in the ledger. Rules load every
   session, so they cost context; keep them few.
4. A project skill under the host's project skills directory: `/ploma:learn --skill <name>`, for a repeatable
   multi-step procedure.
5. Nowhere: a stale or one-off lesson is deleted.
