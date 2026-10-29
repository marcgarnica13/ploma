---
type: llm
---

Pass only if every claim below holds for the final response:

1. It ran the compile script once per build and quotes the report's status line (PASS or FAIL).
2. On PASS it states the page count and the page budget of 8 with its status; on FAIL it names the reason the report gives (a missing build tool, a build exit code, a log error, undefined citations or references, or the page budget).
3. If the log holds errors, it quotes only the first error with its file and line, says to fix the first error, not the last, and proposes one concrete fix without applying it.
4. It does not edit any .tex or .bib file, and it does not rebuild without the user's approval.
5. It does not show a Python traceback as the result.
6. It ends with one next-step line: /ploma:validate-bib after a clean build, /ploma:format when over budget, or fixing the named error or tool otherwise.
