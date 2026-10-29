---
type: llm
---

Pass only if every claim below holds for the final response:

1. It quotes the summary table with the columns Check, Critical, Medium and Low, and the verdict line, which is PASS.
2. It says that every cited key resolves and that one entry is unused, without listing unrelated detail.
3. It does not claim that any entry was verified online (this run is structural and makes no lookups).
4. It does not edit any .bib or .tex file and does not offer to.
5. It ends with one next-step line recommending /ploma:validate-bib --semantic before submission.
