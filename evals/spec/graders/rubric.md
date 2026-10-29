---
type: llm
---

Pass only if every claim below holds for the run:

1. The spec has the template's sections: Identity, Venue constraints, Claims and evidence, Evaluation plan, Positioning, Section architecture with target pages, Locked decisions, Open questions, Figures needed.
2. Venue constraints come from the config: generic-conference, a page budget of 8 pages excluding references, anonymized.
3. The locked decisions include the decisions from the existing log under quality_reports/decisions/, each citing that log as its source, and those decisions are not asked again.
4. Each claim has an evidence pointer that is a real file:line in the sections or a results key such as results/metrics.json:avg_fitness, or is marked planned.
5. The figure row gives the source script from the manuscript's ploma:source line (scripts/make_fig1.py --season 2023).
6. Every turn that asks the user something asks one or two questions, each with the first option marked as recommended and a reason.
