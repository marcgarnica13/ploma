# Paper Spec: Tracing Agentic Workloads at Scale

**Status:** binding contract for /ploma:write
**Created:** 2026-10-30
**Updated:** 2026-10-30
**Paper type:** Empirical study
**Discipline card:** generic
**Decision log:** quality_reports/decisions/2026-10-30_intro.md

## Identity

Hawser is a tracer for LLM agents that records the causal link from each model decision to the tool results it consumed, and on 1200 tasks across three agent frameworks it cuts median trace-query latency by 27.4% against an OpenTelemetry pipeline at 1.1 times the storage, for operators who debug failed agent runs.

## Venue constraints

| Constraint | Value | Source |
|---|---|---|
| Venue profile | generic-conference: Generic conference | venue.profile |
| Page budget | 10 pages, references excluded | venue.page_budget, venue.page_budget_includes_refs |
| Anonymity | not anonymized | document.anonymized |
| Citation style | numeric | venue.cite_style |
| Document class | article | venue.doc_class |
| Venue bar | A crisp, novel contribution with an evaluation strong enough to believe the main claim, presented clearly within the page limit. | the profile |

## Claims and evidence

| ID | Claim | Evidence | Status |
|---|---|---|---|
| C1 | Hawser's trace model links each model decision to the tool results in its context, so a task's trace is a DAG rather than a tree of spans. | sections/method.tex:5-9 | supported (design) |
| C2 | Hawser's query planner answers causal questions by walking indexed edges backwards instead of scanning whole traces. | sections/method.tex:12-16 | supported (design); no isolated measurement (L2) |
| C3 | Against an OpenTelemetry pipeline, Hawser cuts median trace-query latency by 27.4%. | results/bench.json:latency_cut_vs_otel_pct; sections/results.tex:6 | supported |
| C4 | Against raw logs searched by identifier, Hawser cuts median trace-query latency by 41.2%. | results/bench.json:latency_cut_vs_rawlogs_pct; sections/results.tex:7 | supported |
| C5 | Hawser stores 1.1 times the bytes of the OpenTelemetry pipeline. | results/bench.json:storage_ratio; sections/results.tex:8 | supported |
| C6 | The evaluation covers 1200 tasks across three agent frameworks. | results/bench.json:n_tasks, results/bench.json:n_frameworks; sections/results.tex:4 | supported |
| C7 | Each latency cut carries a 95% bootstrap confidence interval. | planned: bootstrap over tasks, new results keys for the lower and upper bound per baseline | planned |

## Evaluation plan

- **Method:** Run 1200 tasks on three agent frameworks, trace each with Hawser and with each baseline back end, and issue the same set of causal queries against each (sections/results.tex:4).
- **Evaluation regime:** Same tasks and same queries for every back end; paired comparison of median query latency. Evaluation setup names the three frameworks, the task source, and the number and kinds of causal queries (L6).
- **Baselines:** OpenTelemetry pipeline (the realistic production baseline, headline); raw logs searched by identifier (the floor).
- **Metrics:** Reduction in median trace-query latency (%, higher is better); storage as a multiple of the OpenTelemetry pipeline's bytes (lower is better).
- **Variability:** 95% bootstrap confidence interval on each latency cut, reported in Table~\ref{tab:results} (L7, C7).
- **Ablations and robustness:** None. The planner's share of the latency gain is not isolated (L2).
- **Threats:** Sample: frameworks, tasks and queries described (L6). Variability: bootstrap intervals (L7). Comparison fairness: every back end is timed on the same unsampled trace sets, stated in Evaluation setup (L8). Claim and evidence match: covered by C3-C6. Reproducibility: code release and rerun command (L4).

## Positioning

| Closest work | What it does | This paper's delta | Cite key |
|---|---|---|---|
| Mace et al. (2015), Pivot Tracing | Dynamic causal monitoring by propagating metadata with requests | Hawser applies metadata propagation to model decisions and the tool results they read | Mace2015 |
| Kaldor et al. (2017), Canopy | End-to-end performance tracing and analysis at scale | Canopy models spans of requests; Hawser models decision-to-result edges | Kaldor2017 |
| Sambasivan et al. (2016) | Principles of workflow-centric tracing | Hawser treats the agent's decision chain as the workflow | Sambasivan2016 |
| Las-Casas et al. (2018, 2019) | Biased and scalable trace sampling | Hawser reuses whole-trace sampling to bound storage | LasCasas2018, LasCasas2019 |
| LLM-agent observability and tracing tools | open, pending /ploma:lit-review (L9) | open | TO VERIFY |

## Section architecture

| Section | File | Purpose | Claims served | Target pages |
|---|---|---|---|---|
| Introduction | sections/intro.tex | Problem, Hawser, headline result and cost, contributions | C1-C3, C5, C6 | 1.5 |
| Related work | sections/related.tex (new) | Distributed tracing, trace sampling, agent observability (L9) | positioning | 1.5 |
| Method | sections/method.tex | Causal trace model and query planner, with F1 | C1, C2 | 2.5 |
| Evaluation setup | sections/setup.tex (new) | Frameworks, tasks, query set, baselines, unsampled timing, bootstrap | C6, C7 | 1.5 |
| Results | sections/results.tex | Latency cuts with CIs, storage, F2 | C3-C5, C7 | 1.5 |
| Limitations and conclusion | sections/conclusion.tex (new) | No planner ablation (L2), scope of three frameworks, code availability (L4) | all | 1.0 |

**Total:** 9.5 of 10 pages (references excluded), 0.5 page slack.

## Locked decisions

| ID | Decision | Choice | Rationale | Source |
|---|---|---|---|---|
| L1 | Headline latency number and baseline | 27.4% vs OpenTelemetry; 41.2% vs raw logs stays in Results | Matches bench.json, the abstract and results.tex:6; strongest baseline | decisions/2026-10-30_intro.md#D1 |
| L2 | Query planner contribution | Keep as contribution two with a pointer to Section 2; never attribute a share of the 27.4% to it | Described in method.tex:12-17; no ablation exists | decisions/2026-10-30_intro.md#D2 |
| L3 | Storage cost in the intro | One sentence: 1.1 times the OpenTelemetry pipeline's bytes | Small overhead stated up front pre-empts the referee question | decisions/2026-10-30_intro.md#D3 |
| L4 | Reproducibility | Release code and traces; set `pipeline.rerun`; one-line availability statement | Lets the audit regenerate bench.json | decisions/2026-10-30_intro.md#D4 |
| L5 | Paper type | Empirical study | The generic card's only type | the repo (disciplines/generic.yaml) |
| L6 | Evaluation sample description | Name the three frameworks, the task source, and the number and kinds of queries in Evaluation setup (L10) | Clears the card's sample check for about 0.3 pages | interview 2026-10-30 |
| L7 | Variability | 95% bootstrap CI on each latency cut, in the results table | Answers the card's variability check; needs new results keys and a rerun | interview 2026-10-30 |
| L8 | Comparison fairness under sampling | Time queries on identical, unsampled trace sets on every back end; state it in Evaluation setup | The cut then isolates the trace model and planner, not sampling | interview 2026-10-30 |
| L9 | Positioning against agent-observability work | Run /ploma:lit-review before writing related work | Finds and verifies the closest agent-tracing work before the delta is written | interview 2026-10-30 |
| L10 | Section architecture | Six sections: Intro 1.5, Related work 1.5, Method 2.5, Evaluation setup 1.5, Results 1.5, Limitations and conclusion 1.0 | 9.5 of 10 pages leaves slack; gives L6 and L9 a home; the card rewards an honest limitations section | interview 2026-10-30 |
| L11 | Figures | F1 overview DAG, F2 latency CDF | F1 conveys the core idea at a glance (venue peeve); F2 shows spread (L7) | interview 2026-10-30 |

## Open questions

- **Q1:** The staged intro states "31%" with no baseline (sections/intro.tex:7). Why it matters: it contradicts L1 and bench.json. Recommended: redraft the intro to 27.4% vs OpenTelemetry before commit.
- **Q2:** `pipeline.rerun` is not set in ploma.yaml. Why it matters: L4 depends on it. Recommended: set it, then re-run /ploma:onboard.
- **Q3:** The framework names, task source and query set are facts only the author has. Why it matters: L6 cannot be written without them. Recommended: supply them before /ploma:write setup.
- **Q4:** The bootstrap CI keys do not exist in results/bench.json yet. Why it matters: C7 is planned until the pipeline emits them. Recommended: add them, rerun, then add the key names to `pipeline.metric_keys`.
- **Q5:** Whether the existing bench.json numbers were already measured on unsampled, identical trace sets. Why it matters: if not, C3-C5 must be rerun under L8. Recommended: check the benchmark code before writing Results.
- **Q6:** The agent-observability positioning row is empty. Why it matters: the venue weights novelty at 0.30. Recommended: run /ploma:lit-review on LLM-agent tracing and observability (L9).
- **Q7:** F2 has no source script yet. Why it matters: figure provenance and the audit. Recommended: write a plotting script under the pipeline that reads the per-query latencies, and put a `% ploma:source <script>` line before its `\includegraphics`.
- **Q8:** The code availability statement needs a URL or archive. Why it matters: L4. Recommended: place it in the conclusion, with the URL supplied by the author.

## Figures needed

| ID | Shows | Claim | Section | Source script |
|---|---|---|---|---|
| F1 | One task traced two ways: a tree of independent spans next to Hawser's decision-to-result DAG | C1 | Method (referenced from Intro) | none (diagram, drawn by hand or in TikZ) |
| F2 | CDF of per-query latency for Hawser, the OpenTelemetry pipeline and raw logs | C3, C4, C7 | Results | unknown (Q7) |

## Post-flight verification

Skipped (--no-verify).
