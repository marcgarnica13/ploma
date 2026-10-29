---
type: llm
---

Pass only if every claim below holds for the run:

1. The review reads the existing bibliography (refs.bib) and does not suggest Bradley1952, Elo1978 or Hunter2004 again as new entries.
2. Every suggested BibTeX entry was written to a candidates file and checked with the citation lookup script before it was offered; only entries the script reported as verified appear under "Key Papers (VERIFIED)" and "BibTeX Entries (VERIFIED)", and every other candidate (partial, not_indexed, unreachable, skipped, mismatch, missing) is listed under "TO VERIFY" with its status and evidence, not under Key Papers. Papers already in refs.bib appear only in their own "Already in your bibliography" section, not under Key Papers (VERIFIED).
3. The report follows the shape: Summary, Key Papers (VERIFIED), Already in your bibliography, TO VERIFY, Thematic Organization, Positioning against this paper, Gaps and Opportunities, Suggested Next Steps, BibTeX Entries (VERIFIED), Post-flight verification.
4. A claim-verifier agent receives the claims, questions and source pointers but not the drafted review, and the outcome (PASS, PARTIAL or FAIL) is reported.
5. The reply says nothing was written to the bibliography and tells the user to copy the verified entries and run the semantic bibliography check.
