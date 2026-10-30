# Decision log: intro

**Date:** 2026-10-30
**Input:** sections/intro.tex
**Status:** complete

## Summary

| ID | Decision | Answer | Lens |
|---|---|---|---|
| D1 | Headline latency number and baseline | 27.4% vs OpenTelemetry | Empiricist |
| D2 | Query planner contribution | Keep it, point to Section 2 (method) | Theorist |
| D3 | Storage cost in the intro | Yes, one short sentence (1.1x vs OpenTelemetry) | Pragmatist |
| D4 | Reproducibility commitment | Release code + rerun command | Reproducibility |

## Settled by the repo

| Decision | Answer | Evidence |
|---|---|---|
| Task count in the evaluation claim | 1200 tasks | sections/intro.tex:12; results/bench.json `n_tasks` = 1200 |
| Framework count in the evaluation claim | three frameworks | sections/intro.tex:12; results/bench.json `n_frameworks` = 3 |
| Cited works in the intro exist in the bibliography | Wang2024, Park2023, Sambasivan2016, Kaldor2017 all present | refs.bib:11,21,51,63 |
| Venue and page budget | generic-conference, 10 pages excl. refs, not anonymized | ploma.yaml `venue.*`, `document.anonymized` |
| Storage overhead value | 1.1 times the OpenTelemetry pipeline | results/bench.json `storage_ratio`; main.tex abstract; sections/results.tex:8 |

## Decisions

### D1: Headline latency number and baseline
**Lens:** Empiricist
**Question:** The intro now claims Hawser "cuts median trace-query latency by 31%" with no baseline named (sections/intro.tex:7, staged edit). results/bench.json has 27.4% vs OpenTelemetry and 41.2% vs raw logs, and neither is 31. The abstract and results.tex:6 both use 27.4% vs OpenTelemetry. Which headline number should the intro state?
**Options:**
1. 27.4% vs OpenTelemetry (Recommended): matches bench.json `latency_cut_vs_otel_pct`, the abstract and results.tex:6, and is the strongest realistic baseline.
2. Both: 27.4% vs OTel, 41.2% vs logs: full range up front, one more sentence, invites a weak-baseline objection.
3. Keep 31% (a new result): needs a results key producing 31% and a rerun; the audit fails the claim until then.
**Answer:** 27.4% vs OpenTelemetry (Recommended)
**Rationale:** Matches the results file, the abstract and the results section; strongest baseline.
**Consequences:** The intro must name the OpenTelemetry baseline and state 27.4%; the "31%" in the staged edit is unsupported and must not be committed. The 41.2% raw-logs number stays in Results only.

### D2: Query planner contribution
**Lens:** Theorist
**Question:** The intro lists the query planner as contribution two (sections/intro.tex:11), but it has no section pointer, and results.tex reports only end-to-end latency per baseline. Nothing separates the planner's effect from the causal trace model's (no ablation key in bench.json). How should the intro frame the planner?
**Options:**
1. Keep it, point to Section 2 (Recommended): method.tex:12-17 describes the planner; a pointer costs nothing and the claim stays a design contribution.
2. Fold it into the trace model: two contributions instead of three; the planner reads as an implementation detail.
3. Keep it and add an ablation: strongest claim, needs a new run and a planner-off results key.
**Answer:** Keep it, point to Section 2 (Recommended)
**Rationale:** The planner is described in method.tex:12-17; a pointer is free and the claim does not assert a share of the latency gain.
**Consequences:** Contribution two gets `(Section~\ref{sec:method})`. The intro must not attribute any part of the 27.4% to the planner alone. An ablation stays out of scope for this draft.

### D3: Storage cost in the intro
**Lens:** Pragmatist
**Question:** The abstract states the cost: Hawser stores 1.1 times the bytes of the OpenTelemetry pipeline (main.tex abstract; bench.json `storage_ratio` = 1.1). The intro states only the latency gain (sections/intro.tex:7). Should the intro also state the storage cost?
**Options:**
1. Yes, one short sentence (Recommended): a 10% overhead is small and stating it pre-empts the obvious referee question, for one line.
2. No, leave it to abstract and Results: tighter intro; the cost appears only in Section 3.
**Answer:** Yes, one short sentence (Recommended)
**Rationale:** Small overhead, stated up front, pre-empts the referee question.
**Consequences:** The intro gains one sentence after the latency claim: storage of 1.1 times the OpenTelemetry pipeline's bytes.

### D4: Reproducibility commitment
**Lens:** Reproducibility
**Question:** The intro promises an evaluation on 1200 tasks across three frameworks (sections/intro.tex:12), but ploma.yaml has no `pipeline.rerun` command and the paper names no code or trace release. A referee cannot rerun bench.json as things stand. What should the paper commit to?
**Options:**
1. Release code + rerun command (Recommended): set `pipeline.rerun` and add a one-line availability statement; the audit can regenerate bench.json.
2. Release code, not the traces: raw traces stay private; the paper must say why and offer a substitute.
3. No release in this version: less effort now; reproducibility stays unverifiable and the paper must not imply rerunnability.
**Answer:** Release code + rerun command (Recommended)
**Rationale:** Lets the audit regenerate bench.json and covers the venue's reproducibility weight.
**Consequences:** `pipeline.rerun` must be set in ploma.yaml (then /ploma:onboard). The paper needs a one-line code availability statement (placement left to the spec). Traces are released alongside the code.

## Open

- none

