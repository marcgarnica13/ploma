---
type: llm
---

Pass only if every claim below holds for the final response:

1. It ran the page map script and either quotes its budget line (pages counted against the budget of 8, references excluded) with a section-by-section table of start pages and estimated pages, or, when there is no PDF, says the PDF is missing and recommends /ploma:compile instead of guessing page numbers.
2. Any page number it gives comes from the script output; a section the script did not locate is shown as not found.
3. It does not edit any .tex file and does not claim to have cut anything; a cut plan, if any, is presented as a proposal.
4. It does not record a commit gate entry for format.
5. It ends with one next-step line.
