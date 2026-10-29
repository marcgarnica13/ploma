---
type: llm
---

Pass only if every claim below holds for the run:

1. Exactly one question per assistant turn: every AskUserQuestion call carries a single question, no turn makes two calls, and no extra question is asked in plain text alongside it.
2. Each question has a recommended answer: the first option is labelled as recommended and its description gives the reason, citing a fact from the repo.
3. Before asking, the run looks facts up itself (for example with Grep or Read on the sections, results/metrics.json and refs.bib) and never asks something the repo answers, such as the number of teams, the baselines or the headline metric value.
4. The question names its lens (theorist, empiricist, pragmatist or reproducibility).
5. A decision log is written under quality_reports/decisions/ with the question, its options, the answer (or "unanswered" when no answer came), the rationale and the lens, plus the decisions settled by the repo with their evidence.
