---
type: llm
---

Pass only if every claim below holds for the run:

1. When superpowers:brainstorming is available it is invoked before the research questions; otherwise the reply says superpowers is not enabled and runs the ideation flow alone. No design document is written and no planning skill is invoked.
2. The report holds 3 to 5 research questions ordered from descriptive to application, each with a hypothesis, a method and evaluation plan, data requirements, key assumptions, pitfalls with mitigations, related literature and a paper type taken from the generic discipline card (or unsure).
3. A ranking table by feasibility and contribution follows the questions.
4. Literature, dataset and feasibility claims go to a claim-verifier agent whose prompt holds claims, questions and source pointers but not the drafted report, and the reply ends with a post-flight block giving PASS, PARTIAL or FAIL.
5. No citation is presented as verified without a DOI, URL or bibliography key, and no .tex or .bib file is edited.
