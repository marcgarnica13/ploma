---
type: llm
---

Pass only if every claim below holds for the final response:

1. It contains the doctor's report with the line "Overall verdict:" followed by READY, READY_WITH_WARNINGS or NOT_READY, and the counts line.
2. It ends with a line naming the same verdict.
3. Every FAIL in the report gets one sentence that says what is wrong and gives its remediation (an install command, a config change, or a /ploma: command).
4. Every WARN in the report gets one sentence with its remediation.
5. It does not ask the user whether to proceed, fix, or continue, and it does not offer to fix anything itself.
6. It does not claim to have edited, created or fixed any file.
