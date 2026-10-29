# Manuscript Review: Capturing Team Strategy in European Football via Process Mining and Visual Analytics

**Date:** 2026-06-04
**Reviewer:** review-paper skill (default single-pass, `--no-cross-artifact`)
**File:** manuscript/samplepaper.tex (13 pp, compiles clean)

## Summary Assessment

**Overall recommendation:** Revise & Resubmit (minor–major)

The paper presents a purpose-driven process-mining framework that turns football event data into
interpretable models of team strategy: possessions are filtered by a tactical purpose, abstracted to
`action##zone` activities, and discovered with the Heuristic Miner; the result is rendered as a
"Heuristic map" on the pitch, scored against a directly-follows-graph (DFG) baseline on
fitness/precision/generalization/simplicity, complemented by a season-regularity analysis and a
player-level profile + player→process fit. The work is well-motivated, the pipeline is clearly
described and reproducible, the HM-vs-DFG comparison cleanly answers the "why process mining and not
a plain graph?" question (HM more precise for 19/20 teams), and the interpretation (precision ≈
behavioral predictability) is intuitive and honestly hedged. The revision is in good shape.

Three things hold it back from a clean accept: (1) the **player-level contribution is illustrated on
a single player (Rodri)**, not evaluated — it reads as a promising demo rather than a validated
method; (2) the **DFG is a deliberately weak baseline** and the only one, so "HM is better" is
established only against the simplest possible graph; and (3) the **central tactical interpretation
has no external corroboration** (acknowledged — no ground truth). All three are addressable in an
R&R, mostly by framing and one or two additional analyses; none is fatal.

## Strengths

1. **Clear, reproducible pipeline** with a compact formalism (§3): event → possession → purpose
   filter → `action##zone` activity → event log → discovery → conformance → Heuristic map. A reader
   could reimplement it.
2. **The HM-vs-DFG comparison is the right experiment** and directly answers the prior reviewers'
   "why not a directed graph?" — the DFG hits fitness 1.0 only by being over-general (precision 0.18),
   exactly the point. Replicated across two seasons.
3. **Interpretability is genuinely demonstrated**: the City-vs-Brentford maps and the precision ≈
   predictability reading are concrete and football-sensible, and regularity and precision agreeing
   (Forest as the joint outlier) is a nice internal consistency check.
4. **Honest evaluation framing** (§5.3 states regularity is in-sample; §4 states no ground truth).

## Major Concerns

### MC1: Player-level analysis is a single anecdote, not an evaluation
- **Dimension:** Evaluation & validity
- **Issue:** The featured player contribution (profile + signature-overlap/slot-coverage fit) is
  shown only for **Rodri against three teams** (§5.4). "Fits his own team best" on n=1 player is an
  illustration, not evidence that the fit score is discriminative or meaningful in general.
- **Suggestion:** Either (a) reframe explicitly as a *worked example / proof of concept* (lower the
  claim), or (b) add a lightweight systematic check — e.g., compute fit for many players against
  their own vs. other teams and report how often own-team ranks first, or correlate fit with an
  external role/style label. Even a 20–50 player own-team-rank-first rate would convert the anecdote
  into evidence cheaply.
- **Location:** §5.4, Fig. 6.

### MC2: DFG is the only baseline, and a deliberately weak one
- **Dimension:** Evaluation & validity
- **Issue:** The DFG-as-Petri-net is trivially over-general; beating it on precision is expected and
  does not show HM is a *good* miner, only that dependency filtering helps. The paper is careful to
  frame the DFG as "the simplest directed-graph explanation" (§4), which is fair for the "why not a
  graph" point, but a methods referee will ask for a second, non-trivial baseline.
- **Suggestion:** Add the Inductive Miner (guarantees fitness, is a standard real miner) as one extra
  row in Table 1, or explicitly state why it is out of scope and that the DFG is intended only as the
  graph-mining strawman, not a SOTA comparison.
- **Location:** §4, Table 1.

### MC3: The tactical interpretation is unvalidated against anything external
- **Dimension:** Evaluation & validity / argument
- **Issue:** "We read precision as behavioral predictability" and the City/Brentford readings are
  plausible but rest entirely on internal coherence; there is no external anchor (expert judgment,
  an independent style metric, outcome data). This is acknowledged ("no ground truth"), but it is the
  load-bearing claim of the paper.
- **Suggestion:** Add one external corroboration, even if light: correlate the precision ranking with
  a published style/possession metric (e.g., possession share, PPDA, directness) and report the rank
  correlation. A single significant correlation would substantially de-risk the central claim.
- **Location:** §5.2.

## Minor Concerns

### mc1: Introduction lacks explicit contributions / research question
- The intro (§1) motivates well but never states the research question crisply or enumerates the
  contributions; the abstract carries that load. Add a short "We make the following contributions:"
  list or a one-sentence RQ at the end of §1. (This was an explicit author goal in the revision plan.)

### mc2: Offensive/defensive overclaim
- §1 (line 53) says the paper assumes "the developing of offensive **and defensive** tactics," but
  only offensive (box penetration) is studied. Drop "defensive" or note it as out of scope.

### mc3: Terminology capitalization drift ("Heuristic map")
- "Heuristic map" / "heuristic map" / "Heuristic Map" / "Heuristic maps" appear inconsistently
  (abstract, §4.1 line 108/113, §5.2 line 150/155). Pick one form (suggest "Heuristic map") and apply
  throughout (INV-7).

### mc4: Table 1 caption is not self-contained and is awkwardly worded
- Caption (line 126): "DFG achieves perfect fitness only by being low at precision" — ungrammatical;
  and it no longer names the dataset/season or the 19/20 result. Suggest: "Conformance of the
  Heuristic Miner (HM) vs. the directly-follows-graph (DFG) baseline, English Premier League 2022/23
  (medians over 20 teams; HM precision exceeds DFG for 19 of 20). The DFG reaches perfect fitness only
  at the cost of precision; HM trades some fitness for higher precision, generalization, and
  simplicity."

### mc5: §2 closing sentence on Chan et al. is garbled
- Line 70: "We complement the approach presented by Chan et al. \cite{Chan2025} infering a process
  model that analysts can read..." — missing "by" and a typo ("infering"). Rewrite.

### mc6: Fig. 3 predates the StatsBomb pipeline
- The methodology illustration (Fig. 3, "Heuristic Maps … one match / one season") is from the older
  run and uses the start/end-tendency legend not otherwise foregrounded. It is fine as an
  illustration, but confirm its orientation/zone legend match the current convention, or regenerate
  from the StatsBomb pipeline for consistency.

### mc7: Leftover author note + typos (see Proofread pass for the full list)
- Commented `%IMPORTANT NOT TO MISS…` block (line 72); "steming" (51), "a analysis" (68), missing
  space `source\cite{Decroos2020}` (68), double space "model  all" (168).

## Referee Objections

### RO1: Isn't the DFG baseline a strawman?
**Why it matters:** A methods referee may dismiss the headline "HM far more precise for 19/20 teams"
as beating a model designed to be over-general. **How to address:** add the Inductive Miner row (or
explicitly scope the DFG as the graph-mining strawman that answers "why not a graph," not a SOTA
baseline). See MC2.

### RO2: What does precision *mean* tactically, and how do we know?
**Why it matters:** The paper's interpretive leap (precision = predictability/systematic vs. fluid)
is the contribution; without any external anchor a referee can call it circular. **How to address:**
one external correlation (MC3).

### RO3: Is the player-fit score actually discriminative, or did Rodri happen to fit City?
**Why it matters:** n=1. **How to address:** the own-team-rank-first rate over many players (MC1).

### RO4: Is there leakage between "discovery" and "regularity"?
**Why it matters:** Regularity replays each round against a season model fit on *all* rounds
(including that round). The paper states this is in-sample and makes no transfer claim — good — but a
referee may still want a held-out variant (fit on rounds 1–19, replay 20–38) as a robustness check.
**How to address:** add one held-out split, or keep the honest in-sample framing and explicitly say
the held-out version is future work.

### RO5: Why dependency threshold θ = 0.90 for all teams?
**Why it matters:** A single global threshold could advantage/disadvantage some teams. **How to
address:** the methods note (compact models at no cost in fitness/precision from a sweep) exists in
the repo; surface one sentence of that justification in §4 (currently asserted, not shown).

## Summary Statistics

| Dimension | Rating (1–5) |
|-----------|-------------|
| Argument Structure | 4 |
| Method Soundness | 4 |
| Evaluation & Validity | 3 |
| Literature | 4 |
| Writing | 3.5 |
| Presentation | 4 |
| **Overall** | **3.5 (R&R, addressable)** |
