---
type: llm
---

Pass only if every claim below holds for the final response:

1. It names the draft file sections/intro_suggestion.tex and says the paper itself (main.tex and sections/intro.tex) was not changed.
2. It reports a self-check of the draft: the style check (em-dashes, filler phrases, long sentences) and the consistency check of the numbers, with a verdict or the findings, each finding with a location (file and line), the current text, a fix and a severity.
3. It shows a unified diff of the current introduction against the draft.
4. It lists open flags, or says there are none; it does not edit any other section to resolve a contradiction.
5. The redraft keeps the facts of the current introduction (12 teams, average fitness 0.81) and adds no number that is not in the paper or the results.
6. It ends by offering the merge (/ploma:write with --merge, or a yes) instead of merging on its own.
