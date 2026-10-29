# Session logging

Location: `<outputs.dir>/session_logs/YYYY-MM-DD_description.md`. Logs are gitignored; `/ploma:checkpoint` writes the durable, committed record.

## Three triggers

1. **After plan approval:** write the goal, the approach, the rationale and the key context while it is fresh.
2. **Incrementally:** append one to three lines whenever a design decision is made, a problem is solved, the user corrects something, or the approach changes. Do not batch.
3. **End of session:** a short summary, open questions and blockers.

Start decision lines with `Decision:` or `Decided:`. The pre-compact hook carries those lines across compaction.

The Stop hook reminds you (never blocks) when no log exists or when many responses pass without the newest log changing.
