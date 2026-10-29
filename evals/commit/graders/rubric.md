---
type: llm
---

Pass only if every claim below holds for the run:

1. The skill ran scripts/commit_gate.py prepare before any git command that changes the repository, and quoted its result.
2. The reply says the gate verdict is FAIL because the required bib check failed, and names the missing citation key missingkey2020 (or the bibliography report that lists it).
3. The reply names the next step for the failing check (/ploma:validate-bib or a fix to the citation or the bibliography) and stops; it does not stage, commit, push or open a pull request.
4. No override was recorded: the user wrote no "commit anyway: <reason>" phrase, and the reply does not invent a reason or record one.
5. The reply does not claim the commit happened.
