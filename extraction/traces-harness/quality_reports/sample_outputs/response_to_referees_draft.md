# Response to Referees — DRAFT SCAFFOLD

**Paper:** "Capturing Team Strategy via Process Mining"
**Status:** DRAFT — tracking scaffold, NOT the final response.
**Created:** 2026-06-04

> **What this is.** A living, point-by-point tracking scaffold for the R&R. Every distinct reviewer
> comment is logged below, grouped by reviewer (R1 / R3 / R4 — matching `review/review1-3.md`,
> i.e. Reviewer #1, #3, #4 respectively), mapped to the reviewer-consensus item (C1–C8 / A1–A2 from
> `quality_reports/plans/soft-cooking-seahorse.md`), and given the **planned revision** and a
> **STATUS** (PLANNED / IN-PROGRESS / DONE).
>
> **The actual response prose is intentionally left as `TODO` placeholders.** This document is a
> coverage tracker to be completed (with the final, polite point-by-point prose) in **Phase 4** of the
> plan, once the revisions are implemented. Do not treat the TODO text as a drafted response.

## Decision context

- R1 (Reviewer #1): **Weak reject** — confidence Medium.
- R3 (Reviewer #3): **Reject** — confidence Medium.
- R4 (Reviewer #4): **Weak accept** — confidence Medium.

The editor signalled that an *outstanding* revision addressing all points could flip the decision.

## Consensus-item legend (from the plan)

| Item | Short description |
|------|------------------|
| C1 | Evaluation can't establish validity/usefulness; no baseline |
| C2 | Why process mining, not a directed/attributed graph? |
| C3 | No formalism (define events, traces, methods) |
| C4 | Metrics anecdotal — characterize team or method? |
| C5 | Comparison viz unreadable; highlight differences |
| C6 | Limitations under-discussed (no player info) |
| C7 | Writing quality |
| C8 | Intro promises a player-recruitment use case it never delivers |
| A1 | Sharper research line (author) |
| A2 | References all pre-2023 (author) |

---

## Reviewer R1 (Reviewer #1) — Weak reject

### R1.1 — No justification for process mining vs. directed-graph analysis
- **Comment (quote):** "There is no justification of why process mining is necessary to achieve the
  stated goals. The event sequences and their mapping on the court grid could well be represented by
  directed attributed graphs and methods from the field of graph analysis/mining could be employed to
  extract similar insights."
- **Maps to:** C2 (also motivates C1's baseline).
- **Planned revision:** Literature-backed PM-vs-graph argument in intro/related work (HM recovers
  concurrency/causal dependencies + handles noise via the dependency measure; a raw
  directly-follows/attributed graph does not), cross-referenced to an **empirical DFG baseline** that
  underperforms HM — the DFG *is* the directed-graph alternative. (Plan M4, C2; baseline M1.)
- **STATUS:** PLANNED
- **Response prose:** TODO — Phase 4.

### R1.2 — Lacks formalism / common notation
- **Comment (quote):** "The paper lacks a proper formalism in presenting the framework... the authors
  should try to set up a common notation and framework to properly define the atomic events, the event
  sequences and the analysis using the employed methods."
- **Maps to:** C3.
- **Planned revision:** Compact formal-definitions subsection (§3): event, possession, purpose-trace,
  activity key `action##zone`, model, conformance metrics. Kept tight (≤ half a column). (Plan M3.)
- **STATUS:** PLANNED
- **Response prose:** TODO — Phase 4.

### R1.3 — Evaluation limited; no way to ensure findings are valid/useful (no expert validation)
- **Comment (quote):** "the presented evaluation is quite limited... the authors should demonstrate
  that a) these results are indeed valid... and b) the extracted insights should be useful to experts...
  the evaluation should at least include some focus group discussion involving football experts."
- **Maps to:** C1.
- **Planned revision:** HM-vs-DFG baseline table + precision/simplicity metrics (fitness alone is
  gameable) + explicit metric semantics + within-season round held-out validation as empirical validity
  evidence. **Note:** expert focus group / human ground-truth annotation is **out of scope this round**
  (author decision 2026-06-04) — address as a partial/deferred response with rationale. (Plan M1, M2, C1.)
- **STATUS:** PLANNED
- **Response prose:** TODO — Phase 4. (Must honestly frame the focus-group request as deferred.)

### R1.4 — Figure 4 comparison visualizations hard to compare across teams
- **Comment (quote):** "The visualizations of Figure 4 make it very hard to compare between different
  teams... show only paths/edges that are very different between the two teams, so that their unique
  features are highlighted."
- **Maps to:** C5.
- **Planned revision:** Single difference-pitch comparison figure (signed color scale, only
  above-threshold zone/edge differences shown; shared structure dropped), built on
  `HueristicField.get_overview`. (Plan S1, C5.)
- **STATUS:** PLANNED
- **Response prose:** TODO — Phase 4.

### R1.5 — Writing could be improved
- **Comment (quote):** "The writing of the paper could also be improved."
- **Maps to:** C7.
- **Planned revision:** `/proofread` + de-slop pass (human academic register). (Plan C7.)
- **STATUS:** PLANNED
- **Response prose:** TODO — Phase 4.

### R1.6 — (Summary aside) Unclear what an "event" corresponds to across providers
- **Comment (paraphrase):** Reviewer notes in the summary it is "not entirely clear what an event
  corresponds to since every data provider uses different conventions."
- **Maps to:** C3 (formalism — resolved by the common event/trace definitions).
- **Planned revision:** The §3 formalism defines the atomic event precisely; the methods state the
  provider schema used (StatsBomb open data). (Plan M3.)
- **STATUS:** PLANNED
- **Response prose:** TODO — Phase 4.

---

## Reviewer R3 (Reviewer #3) — Reject

### R3.1 — Lacking technical/methodological contribution; no algorithmic discussion; no method comparison
- **Comment (quote):** "The technical side of contribution is lacking as a submission in the knowledge
  discovery domain, e.g. no algorithmic discussions about the methodology, no comparison with similar
  methods, etc."
- **Maps to:** C1 (baseline comparison) and C2 (method positioning).
- **Planned revision:** HM-vs-DFG baseline head-to-head table (the literal "comparison with similar
  methods"); integrated-framework framing with explicit numbered contributions; formalism §3 grounds
  the methodological discussion. (Plan M1, M6, M3.)
- **STATUS:** PLANNED
- **Response prose:** TODO — Phase 4.

### R3.2 — No proper evaluation / no reference annotations for the task
- **Comment (quote):** "No proper evaluation of the derived analysis, assets, or results. I understand
  that a lack of ground truth makes evaluation difficult, but most other areas... work around this issue
  by creating own reference annotations for the task of interest."
- **Maps to:** C1.
- **Planned revision:** Baseline comparison + precision/simplicity + within-season round held-out
  (reported honestly as in-sample regularity). **Reference-annotation / human ground-truth deferred this
  round** — frame as partial with rationale (author scope decision 2026-06-04). (Plan M1, M2, M10.)
- **STATUS:** PLANNED
- **Response prose:** TODO — Phase 4. (Honest framing of the deferred annotation evaluation required.)

### R3.3 — Metric use unclear/anecdotal; do fitness & generalization characterize team or method?
- **Comment (quote):** "The use of metrics is not clear and mostly anecdotal — you have two metrics
  fitness and generalization... but it's not clear whether the metrics can be used to characterize
  Teams... or the discovery method." Also: "I struggle to understand how the two metrics fitness and
  generalization are used in the related literature."
- **Maps to:** C4.
- **Planned revision:** Explicit metric-semantics paragraph tying fitness/precision/generalization to
  the conformance-checking literature (e.g. Buijs2014/Syring2019); state precisely what each measures
  about the *team* vs the *model*, with the honest caveat that fitness/precision characterize
  *model–log agreement* and are read as team behavioural consistency only under that caveat.
  (Plan M2, C4, M10.)
- **STATUS:** PLANNED
- **Response prose:** TODO — Phase 4.

---

## Reviewer R4 (Reviewer #4) — Weak accept

### R4.1 — Methodology shortcomings not clearly discussed (absence of player information)
- **Comment (quote):** "Shortcomings for the methodology aren't clearly discussed viz. absence of
  player information. Although I suspect this can be managed in future iterations."
- **Maps to:** C6 (and pays off C8).
- **Planned revision:** New **featured player-level analysis section** — per-player precede/follow
  signature within a discovered process + a player→process **fit** score — directly closing the
  "no player info" limitation; residual limitations (off-ball, tracking) still stated explicitly in a
  limitations paragraph. (Plan M12, S2, C6, C8.)
- **STATUS:** PLANNED
- **Response prose:** TODO — Phase 4.

### R4.2 — Visualization itself could be improved
- **Comment (quote):** "There's a myriad of passing visualizations available in soccer. Although there's
  novelty in purpose definition for sequence extraction the visualization itself could be much improved."
- **Maps to:** C5.
- **Planned revision:** Difference-highlighted Heuristic Map (single difference-pitch) plus regenerated
  figures from the new-data run. (Plan S1, C5.)
- **STATUS:** PLANNED
- **Response prose:** TODO — Phase 4.

---

## Author-initiated items (not raised by a referee, tracked for completeness)

### A1 — Sharper research line
- **Maps to:** A1.
- **Planned revision:** Intro rewrite with explicit numbered contributions and integrated-framework
  framing. (Plan M6.)
- **STATUS:** PLANNED
- **Response prose:** N/A (author-side; reflected in revision summary, not a referee reply).

### A2 — References all pre-2023
- **Maps to:** A2.
- **Planned revision:** `/lit-review` 2023–2026; integrate ~12–18 entries; every new `\cite` resolves
  in `mybib.bib` and is DOI-verified. (Plan M7.)
- **STATUS:** PLANNED
- **Response prose:** N/A (author-side; reflected in revision summary).

### C8 — Intro promises a player-recruitment use case it never delivers
- **Maps to:** C8 (self/intro gap; reinforced by R4.1).
- **Planned revision:** Player→process **fit** score pays off the promise ("would player X suit team Y's
  process?"). (Plan M12, C8.)
- **STATUS:** PLANNED
- **Response prose:** TODO — Phase 4 (folded into the R4.1 reply and the revision summary).

---

## Coverage checklist (consensus items → status)

| Item | Covered by | STATUS |
|------|-----------|--------|
| C1 | R1.3, R3.1, R3.2 | PLANNED |
| C2 | R1.1, R3.1 | PLANNED |
| C3 | R1.2, R1.6 | PLANNED |
| C4 | R3.3 | PLANNED |
| C5 | R1.4, R4.2 | PLANNED |
| C6 | R4.1 | PLANNED |
| C7 | R1.5 | PLANNED |
| C8 | C8 / R4.1 | PLANNED |
| A1 | A1 | PLANNED |
| A2 | A2 | PLANNED |

**Open framing note for Phase 4:** R1.3, R3.2 request expert/human-annotation validation that is
**out of scope this round** (author decision). The final response must address these honestly as
partial/deferred with the empirical-validity substitutes (baseline + precision/simplicity + held-out
regularity) and a clear rationale — not claim them fully addressed.
