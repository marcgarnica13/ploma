---
type: llm
---

Pass only if every claim below holds for the final response:

1. It lists the extracted claims with ids, including the citation claims about Bradley1952, Elo1978 and Hunter2004.
2. It reports a per-claim verdict with a tier (none, LOW, MED or HIGH) and a result line of PASS, PARTIAL or FAIL.
3. A source it could not reach is reported as unverifiable (MED or LOW), never as a contradiction or a fabricated reference.
4. It says which claims gate entry was recorded: FAIL only when a HIGH-WARN exists, PASS otherwise.
5. It does not edit any .tex or .bib file and ends with one next-step line.
