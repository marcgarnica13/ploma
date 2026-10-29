---
type: llm
---

Pass only if every claim below holds for the final response:

1. It reports on all four files: main.tex and sections/intro.tex, sections/method.tex and sections/results.tex, with the issue count per file and a breakdown by severity (HIGH, MEDIUM, LOW).
2. Every finding it highlights gives a location (file and line or section), the current text quoted, and a proposed fix.
3. It says the gate entry recorded for proofread: PASS when there is no HIGH finding, otherwise WARN with the number of open HIGH findings.
4. It does not edit any .tex or .bib file and does not claim to have applied a fix; it says fixes are applied only after the user approves them.
5. It ends with one next-step line.
