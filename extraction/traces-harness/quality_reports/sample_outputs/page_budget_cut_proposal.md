# Proposal: Fitting the revised manuscript to 9 pages (ADS) without losing content

**Date:** 2026-06-04
**Status:** DRAFT — awaiting author validation
**Context:** Revised body is ~16 pp now, ~19 pp projected once the featured player-analysis section and
the HM-vs-DFG results table land. ADS limit is **9 pages + references** (references are pages 17–20 now
and do **not** count). Goal of this doc: show how to reach 9 body pages **while keeping every
contribution** — i.e. compress and relocate, do not delete substance.

> Note: author has since said the limit was "restored, proceed with all." This proposal is kept as the
> record of HOW a 9-page version would be built, in case a conference (vs journal) target is chosen.
> If we go journal, none of these cuts are needed.

---

## Where the pages actually go (measured)

| Block | Pages (approx) | Counts toward 9? |
|---|---|---|
| Body text (6,614 words) | ~12 if pure text | yes |
| 5 full-width floating figures | +~3–4 (whitespace + float pages) | yes |
| References (17–20) | ~4 | **no — free** |

Two levers: **(L1) prose density** and **(L2) figure/float footprint**. L2 is the cheapest win and
loses zero content.

---

## Principle: compress + relocate, don't delete

Every reviewer-addressing addition stays in the paper. We (a) reclaim whitespace, (b) tighten prose,
(c) move detail (not contribution) to a self-contained **online supplement** the paper already uses
(the Supplementary Information link). ADS allows an online appendix; the 9 pages carry the argument,
the supplement carries the depth.

---

## Cut/compress plan (ordered by value-per-page, ~10 pp to recover)

### A. Figure & float footprint — reclaim ~3 pp, zero content loss
1. **Merge Fig. 1 (methodology) + Fig. 2 (purpose-trace example)** into one two-panel figure. (~0.7 pp)
2. **Make Figs. 4–5 single-column** (`width=0.5\textwidth`, wrapped) where legible, or combine the
   City/United maps into one panel with the **difference-pitch** (which we're building anyway — it
   replaces two full maps with one). (~1.5 pp)
3. **Tighten float placement** (`[t]`/`[h]`, smaller `\textwidth` fractions) to kill float-induced
   half-empty pages. (~0.8 pp)

### B. Related work — compress ~1.5 pp, keep all citations
4. Section 2 is currently long-form prose. Convert the historical survey paragraphs to **2–3 tight
   sentences each**; keep every citation (citations are free). The new graph/GNN + PM positioning
   stays (it's load-bearing for C2). (~1.5 pp)

### C. Discussion — compress ~1.5 pp
5. The Discussion repeats methodology and speculates at length. Cut speculative/future-work prose to a
   short paragraph; keep the limitations paragraph (answers C6). (~1.5 pp)

### D. Relocate depth to the online supplement — reclaim ~2.5 pp, content preserved off-page
6. **Per-team full metrics table** → supplement; in the body keep a **compact summary** (median HM vs
   DFG per metric + the key contrast rows, e.g. City/Arsenal). (~1 pp)
7. **Petri-net / heuristic-net worked example + zone-grid construction detail** → supplement (already
   gestured at). Body keeps the heuristic-map reading. (~0.8 pp)
8. **Second purpose (build-up) full results** → supplement as the "framework generalizes" evidence;
   body keeps one figure + one paragraph. (~0.7 pp)

### E. Player-analysis section — keep featured but lean — net author decision
9. Present the player profile + player→process fit with **one worked example** (one player, one target
   team) in the body; move the methodology detail + extra examples to the supplement. Keeps it a
   featured contribution while costing ~1 pp instead of ~3.

---

## Resulting budget (body pages, target ≤ 9)

| Section | Now (proj.) | After plan |
|---|---|---|
| Intro | 1.5 | 1.0 |
| Related work | 2.5 | 1.0 |
| Formalism + trace construction | 2.5 | 1.5 |
| Discovery + evaluation (+DFG table) | 3.0 | 1.5 |
| Experiments (2 purposes) + figures | 4.5 | 2.0 |
| Player analysis (featured, lean) | 3.0 | 1.0 |
| Discussion + limitations | 2.0 | 1.0 |
| **Total body** | **~19** | **~9** |

---

## What is NOT cut (non-negotiable contributions)
- The integrated framework + numbered contributions (C-A1).
- Formalism block (C3).
- HM-vs-DFG baseline + precision/simplicity + metric semantics (C1, C2, C4).
- Featured player profiling + player→process fit (C6, C8) — leaned, not dropped.
- The 2023–2026 references (free) and the "why PM not a graph" argument (C2).

## Risk
- Heavy reliance on an online supplement: acceptable for ADS, but the **body must stand alone** — each
  relocated item needs a one-line in-body pointer.
- If the author prefers no supplement dependence, the only alternative to reach 9 pp is the **split**
  (player analysis → separate paper). Flagged earlier as Option "Two papers."

## Recommendation
If conference: execute A→D fully (recovers ~8.5 pp with zero contribution loss), then E if still over.
If journal: skip this; keep full length.
