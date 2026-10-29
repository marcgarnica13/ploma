---
type: llm
---

Pass only if every claim below holds for the run:

1. The reply prints a Pre-Flight Report whose venue line says the key quantum-letters was not found.
2. It lists the available venue keys as reported by the profiles script (for example acm-sigconf, generic-conference, generic-journal, springer-ml), not a list invented from memory.
3. It stops before any review starts: no editor, referee or other agent is spawned, and no review report is written.
4. It tells the user how to continue: re-run with one of the listed keys, or add a project venue profile.
