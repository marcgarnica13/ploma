# Plan: Outstanding R&R revision — "Capturing Team Strategy via Process Mining"

**Status:** DRAFT (awaiting approval)
**Date:** 2026-06-04
**Plan file:** `quality_reports/plans/soft-cooking-seahorse.md`

## Context

The paper was submitted to a conference **ADS track** and received three reviews
(`review/review1-3.md`): **weak-reject (R1)**, **reject (R3)**, **weak-accept (R4)**. The editor
signalled that an *outstanding* revision addressing all points could flip the decision. This plan
turns that signal into a concrete revision.

**Container decision DEFERRED (author, 2026-06-04):** Originally scoped as **9 pages + references**,
ADS conference (LLNCS, INV-1/INV-2). Scope has since grown to two new analytical contributions
(build-up purpose + featured player-level analysis) plus rigor upgrades — now genuinely journal-sized.
**Decision:** *draft all the content first* (favouring the concise option where natural), **do NOT cut
to 9 pages during drafting**, then **evaluate the container** (stay 9pp ADS / move to a longer journal /
split into two papers) once the real size is visible. The 9-page limit is therefore a **post-draft
evaluation**, not a drafting constraint. References never count toward page budget regardless.

**Author decisions (2026-06-04):**
- Venue: **conference ADS track**, 9 pp + refs (not the Springer ML journal — so the `--peer ML`
  profile is only a stress-test lens, not the calibration target).
- Evaluation upgrade scope: **DFG baseline comparison + precision + simplicity metrics** (no expert
  focus group, no human ground-truth annotation this round).
- **CONFIRMED (2026-06-04):** *Keep the **DFG** as the single comparison baseline* (Heuristic Miner vs
  DFG). It does double duty: R3's literal head-to-head baseline **and** R1's "why not a plain directed
  graph?" answered empirically. We **also** back C2 with a literature-grounded argument. **No Inductive
  Miner** (keep it to one baseline for page budget; MAY add if space allows).
- **Data loading: read StatsBomb JSON directly** — do **not** upload to Mongo.
- Experiments: **full re-run on NEW data** — confirmed source: `/home/marc/Documents/statsbomb_data/data/`
  (StatsBomb open-data JSON: `matches/lineups/events`, plus `360`/`360-frames`).
  **Competition 2 = Premier League, two seasons: 108 = 2021/22 and 235 = 2022/23** (580 event files).
  Upgrade over the old EPL 2017/18 run: **two recent seasons** → enables a cross-season
  external-validity / regularity story (promotes Y1 to feasible). 360 freeze-frames are a future lever
  for R4's off-ball limitation (out of scope this round; mention as now-feasible future work).
- Contribution framing: **integrated framework** (purpose-driven traces + discovery + Heuristic Maps
  + regularity + **player-level profiling & player-to-process fit**), presented as one coherent pipeline.
- **Player-level analysis = FEATURED contribution** (own section): per-player precede/follow signature
  within a discovered process + a player→process **fit** score. Closes R4's "no player info" limitation
  and delivers the recruitment use case the intro already promises but never paid off.

### The reviewer consensus (what the revision must answer)

| # | Reviewer point | Raised by | How this plan answers it |
|---|---|---|---|
| C1 | **Evaluation can't establish validity/usefulness; no baseline** | R1-W3, R3-W1/W2 | **HM vs DFG baseline table** + **precision/simplicity** metrics (fitness alone is gameable) + explicit metric semantics + **cross-season held-out validation** (train season A, test season B) as empirical validity evidence |
| C2 | **Why process mining, not a directed/attributed graph?** | R1-W1 | **Both:** literature-backed argument (HM recovers concurrency/causal dependencies + handles noise via the dependency measure; a raw directly-follows/attributed graph does not) **and** the empirical **DFG baseline** showing it underperforms HM — the DFG *is* the directed-graph alternative |
| C3 | **No formalism** (define events, traces, methods) | R1-W2 | Compact formal-definitions subsection (§3) |
| C4 | **Metrics anecdotal — characterize team or method?** | R3-W3 | Explicit metric-semantics paragraph tying fitness/precision/generalization to Buijs2014/Syring2019; state precisely what each measures about the *team* vs the *model* |
| C5 | **Comparison viz unreadable; highlight differences** | R1, R4 | Difference-highlighted Heuristic Map for the two-team comparison (SHOULD) |
| C6 | **Limitations under-discussed (no player info)** | R4 | **Now directly answered by the featured player-level analysis** (player profiling + fit); residual limitations (off-ball, tracking) still stated explicitly |
| C8 | Intro promises a player-recruitment use case it never delivers | (self/intro gap) | Player→process **fit** score pays off the promise: "would player X suit team Y's process?" |
| C7 | **Writing quality** | R1 | `/proofread` + de-slop pass (no AI-slop register) |
| A1 | Sharper research line | author | Intro rewrite: explicit numbered contributions, integrated-framework framing |
| A2 | References all pre-2023 | author | `/lit-review` 2023–2026; integrate ~12–18 entries (refs are free vs page budget) |

## Requirements (MUST / SHOULD / MAY)

**MUST**
- M1. **HM vs DFG baseline comparison** on the new data (one comparison miner), reported as a table,
  plus **within-season round held-out** (per-round replay against the season model), reported
  **honestly as in-sample regularity** (INV-8), **per season separately** (2021/22 and 2022/23). No
  cross-season transfer claim. (C1, C2)
- M2. Add **precision** (and **simplicity**) metrics alongside fitness/generalization; state metric semantics explicitly. (C1, C4)
- M3. Compact **formalism** subsection: event, possession, purpose-trace, activity key `action##zone`, model, conformance metrics. (C3)
- M4. **Motivate process mining vs. graph mining** in intro/related work via a **literature-backed
  argument** (concurrency/causal dependency recovery, noise handling), cross-referenced to the DFG
  baseline result. (C2)
- M5. **Re-run the full pipeline on the NEW dataset** and regenerate **all** reported numbers + figures from source (SSOT rule — no hand-edited numbers). (experiments)
- M6. Sharpen research line: intro with **explicit numbered contributions**, integrated-framework framing. (A1)
- M7. References updated to include **2023–2026** work; every new `\cite` resolves in `mybib.bib` (INV-5) and is DOI-verified. (A2)
- M8. **Page length: DEFERRED.** Draft all content first; do not cut to 9 pp during drafting. After a
  full draft, produce a page-budget breakdown and decide container (9pp ADS / journal / split).
- M12. **Featured player-level analysis** (own section): (a) **player profile** = distribution of
  directly-preceding and directly-following activities (`action##zone`, with zone/resource) around each
  player's events inside a discovered process; (b) **player→process fit** = score matching a player's
  input/output signature to the transition slots of another team's discovered model, with worked
  examples ("would player X fit team Y's process?"). Uses the **resource (player)** already tagged in
  `create_event_log`. (C6, C8)
- M9. **Point-by-point response-to-referees** document.
- M10. Honest evaluation framing (INV-8): report the regime each metric was measured under.

**MUST (revised scope)**
- M11. **Second analysis purpose = build-up from the goalkeeper** (possessions starting at the GK /
  defensive third and progressing out of the defensive third), added alongside "penetrate the box" to
  demonstrate the framework generalizes across analysis questions (integrated-framework + flexibility
  claim, R4's praised novelty). Needs a new `filter_buildup_*` in `logic/filters.py` + one extra run set.

**SHOULD**
- S1. Difference-highlighted comparison visualization = **(a) single difference pitch**: one map, signed
  color scale, only above-threshold zone/edge differences between two teams shown (drops shared
  structure, saves page space). Built on `HueristicField.get_overview` aggregation. (C5)
- S2. Explicit **limitations** paragraph incl. absence of player/off-ball info. (C6)
- S3. Tighten Related Work + Discussion prose to recover page budget for §3 formalism + baseline table.

**MAY**
- Y1. Broaden beyond one league/season if the new data supports it (external validity) — only if page budget and data allow.
- Y2. Time-aware semantics note as future work (already gestured at in Discussion).

**Clarity status**
- CLEAR: venue, eval scope, contribution framing, page limit, **data source** (StatsBomb open-data
  JSON, PL 2021/22 + 2022/23).
- TO RESOLVE AT EXECUTION: load path — `upload-to-mongo` (via `sports_pm/scripts/stats_bomb.py`) to
  feed the existing Mongo-based runner, **vs.** point the loader at local JSON. Pick the lower-risk path
  at Phase 2 start.
- ASSUMED: keep authors anonymized (INV-3) until a non-blind step is requested; keep LLNCS/pdflatex (INV-1/2).

## Working style (author preference, 2026-06-04)

**At every reasoning fork or design choice, STOP and present options for the author to pick — do not
decide unilaterally.** Execution is **checkpoint-based**: pause at each phase boundary (and at any
in-phase fork) to show options/results before proceeding. This applies throughout implementation, not
just planning.

## Approach (phased; Phase 2-runs gated on data)

### Phase 1 — Literature refresh (NOT blocked on data; start immediately)
- `/lit-review` on three strands, 2023–2026:
  1. process mining / process discovery in **sports & invasion-sport tactics**;
  2. soccer **tactic/style discovery** (sequence mining, motifs, GNN/graph approaches, tactic detection) — needed to sharpen the *PM-vs-graph* positioning (C2);
  3. recent **process-discovery / conformance** advances (precision measures, miners) to support §3/§4.
- Extract BibTeX → append to `manuscript/mybib.bib`.
- `/validate-bib --semantic` (DOI check via Crossref/Semantic Scholar/OpenAlex) + `/verify-claims` (CoVe) on every new citation's claim.
- Output: a short positioning note (where this work sits vs 2023–2026 graph/sequence methods) feeding §1/§2.

### Phase 2 — Pipeline upgrade (minimal code; JSON-driven)
Code:
- `src/sports_pm/logic/discovery.py`: add a **`get_dfg_baseline(...)`** (pm4py `discover_dfg` +
  `convert_dfg_to_petri_net`, scored with the same token-replay) and add **precision**
  (`pm4py.algo.evaluation.precision...`) + **simplicity** to the metric set returned alongside the
  existing fitness/generalization. Mirror the existing pattern. **DFG only — no Inductive miner.**
  Respect INV-9 (seed/determinism), INV-11 (`action##zone` key untouched), INV-12 (standardized-space zoning).
- **JSON loader (not Mongo):** point/adapt the StatsBomb path to read
  `/home/marc/Documents/statsbomb_data/data/{matches,events,lineups}` directly. Check whether
  `parse_statsbomb_matches.py` / `get_match_info` can take a file source or needs a thin file-based
  reader bypassing the Mongo client; keep the env-var contract (INV-10), no hard-coded creds.
  StatsBomb open-data schema → `get_play_actions_statsbomb` (native `possession` ids) →
  `..._from_statsbomb` (120×80 → 105×68).
- **Within-season round held-out:** per-round replay against the season model, reported honestly as
  in-sample regularity (INV-8), per season separately. (No cross-season transfer claim.)
- **Second purpose filter:** add `filter_buildup_*` in `src/sports_pm/logic/filters.py` (start at GK /
  defensive third → progress out of defensive third), mirroring `filter_offensive_sequences_statsbomb`
  and stamping `possession_count` case ids.
- (S1) `src/sports_pm/viz/field_graph.py`: **single difference-pitch** mode on `HueristicField` —
  signed zone/edge differences between two teams, threshold-gated, shared structure dropped. ~80–150 lines.
- **Player-level analysis (featured, M12):** new module e.g. `src/sports_pm/logic/player_profile.py`:
  - `player_profile(log, player)` → directly-preceding / directly-following activity distributions
    (`action##zone`) around the player's events, computed on the **resource-tagged** event log; optional
    enrichment with `lineups/` metadata (position).
  - `player_process_fit(profile, target_model)` → fit score matching the player's input/output signature
    to the transitions present in another team's discovered model; worked examples.
  - viz for a player profile (precede/follow on the pitch) + a fit illustration.
  - Keep `##` key (INV-11), standardized zoning (INV-12), determinism (INV-9). **Fit-score definition is
    an execution-time fork — present options at the design checkpoint.**
- `python-reviewer` agent on the changed modules (gotchas: TAGS_FILE import, `##`, coord flip, env contract).

Runs (for BOTH purposes: penetrate-the-box + build-up-from-GK):
- `/data-analysis`: regenerate **HM + DFG** metrics (fitness/precision/generalization/simplicity) +
  within-season round held-out on PL 2021/22 + 2022/23 → write to `src/results/<new-run>/`.
- Regenerate **Table 1** (HM vs DFG metrics) and the regularity figure; produce the **single
  difference-pitch** comparison figure (S1) for a representative team pair, per purpose.
- **Player analysis runs:** compute player profiles (precede/follow) for representative players and one
  or more player→process **fit** examples → results + figures to `src/results/<new-run>/players/`.

### Phase 3 — Manuscript revision (depends on Phase 1 + 2 outputs)
Targeted edits to `manuscript/samplepaper.tex`:
- **§1 Introduction:** rewrite for integrated-framework framing; add **explicit numbered
  contributions**; add the **PM-vs-graph motivation** (C2/M4). (M6)
- **§3 (new subsection) Formalism:** compact definitions (event, possession, purpose-trace, activity
  key, model, conformance metrics). Keep tight — half a column, not a page. (M3)
- **§4 Evaluation:** new **baseline-comparison table** (HM/DFG/IM × fitness/precision/generalization/
  simplicity); **metric-semantics paragraph** (what each measures about *team* vs *model*, C4); honest
  regime statement (M10/INV-8). The DFG row doubles as the "why PM beats a plain graph" evidence (C2).
- **§4.x Data:** update to the new dataset; reconcile all numbers from `src/results/<new-run>` (SSOT).
- **§Experiments figures:** swap in regenerated Figs; (S1) difference-highlighted comparison figure.
- **§ Player-level analysis (NEW featured section):** define the player profile (precede/follow
  signature) + player→process fit; worked examples on the new data; figure(s). Update intro
  numbered contributions to include it. (M12, C6, C8)
- **§Discussion:** residual **limitations** paragraph (off-ball/tracking still absent even with player
  profiling, C6/S2); **tighten** speculative prose to recover space (S3).
- **§2 Related Work:** weave in 2023–2026 refs; **condense** existing prose to stay within budget (S3).
- De-slop / language pass via `/proofread` (human academic register, not AI-slop). (C7)

### Phase 4 — Review, verify, respond, ship
- `/compile-latex` → **check page count ≤ 9 + refs** (M8); resolve overfull boxes / undefined cites.
- `/audit-reproducibility manuscript/samplepaper.tex src/results/` — every number traces to source (cross-artifact rule).
- Adversarial review: `/review-paper --adversarial` and/or `/seven-pass-review`; `/devils-advocate`
  specifically on the *why-PM-not-graphs* argument. (`--peer ML` optionally as a harsher stress lens,
  noting venue is ADS not the ML journal.)
- `/respond-to-referees` — point-by-point response mapping each comment → revision (M9).
- `/validate-bib` + `/verify-claims` final pass.
- Final page-budget enforcement; then `/commit`.

## Files to modify / create

| Path | Change |
|---|---|
| `manuscript/samplepaper.tex` | Intro reframe + numbered contributions; new §3 formalism; new baseline-eval table + metric semantics; new data; **new featured player-level section**; limitations; tightened RW/Discussion; figure swaps |
| `src/sports_pm/logic/player_profile.py` (new) | Player precede/follow profile + player→process fit |
| `manuscript/mybib.bib` | +~12–18 entries (2023–2026), DOI-verified |
| `manuscript/fig4.pdf`, `fig5.pdf` (+ regenerated others as needed) | Regenerated from new-data run; Fig-4 difference-highlighted version (S1) |
| `src/sports_pm/logic/discovery.py` | DFG + Inductive baselines; precision + simplicity metrics |
| `src/sports_pm/viz/field_graph.py` | `ComparativeHeuristicField` / diff mode (S1) |
| `src/notebooks/discovery/parse_*_matches.py` | Point at new data source; emit baseline + precision metrics |
| `src/results/<new-run>/` | Regenerated metrics JSON/CSV + figures (derived, SSOT source for the paper) |
| `quality_reports/` | response-to-referees doc, review/audit reports, session log |

## Reused existing code (don't reinvent)
- `discovery.get_heuristic_net` / `create_event_log` — extend, mirror its token-replay + generalization pattern.
- `viz/field_graph.HueristicField.get_overview` — base for the comparison/diff view.
- pm4py built-ins already imported — `discover_dfg`, `discover_petri_net_inductive`, precision/simplicity evaluators (no new deps; keep `requirements.txt` pinned).
- Harness skills: `/lit-review`, `/data-analysis`, `/audit-reproducibility`, `/validate-bib --semantic`,
  `/verify-claims`, `/proofread`, `/review-paper --adversarial`, `/seven-pass-review`,
  `/devils-advocate`, `/respond-to-referees`, `/compile-latex`, `python-reviewer` agent, `/commit`.

## Verification (end-to-end)
1. **Pipeline:** run the new-data discovery from `src/` with env-vars set (`TAGS_FILE` before import,
   INV-10); confirm `src/results/<new-run>/` non-empty, fitness/precision ∈ [0,1], node names contain
   `##`, no silent empty result on Mongo failure.
2. **Cross-artifact:** `/audit-reproducibility` PASS — every paper number within tolerance of source
   (`replication-protocol.md`); HM vs baselines table matches JSON.
3. **Manuscript:** `cd manuscript && make` clean — no undefined cites, no overfull >10pt, figures render
   with correct pitch orientation/zone legend (INV-4/INV-12), **page count ≤ 9 + refs**.
4. **Bib:** `/validate-bib --semantic` — all `\cite` resolve, DOIs verified, no drift.
5. **Claims:** `/verify-claims` clean on new literature/factual assertions.
6. **Reviewer coverage:** `/respond-to-referees` shows every C1–C8/A1–A2 point mapped to a concrete
   revision (addressed / partially / deferred-with-reason); confirm the player-level section closes C6/C8.
   Spot-check player profiles/fit outputs in `src/results/<new-run>/players/` are non-empty and sensible.
7. **Adversarial:** `/seven-pass-review` / `--adversarial` surface no remaining critical issue.

## Risks & mitigations
- **Page budget vs. additions** — biggest risk. Mitigation: S3 cuts are *required*, not optional;
  enforce a page-count gate every compile; formalism stays ≤ half a column.
- **New-data blocker** — Phases 1 + Phase-2-code proceed without it; only runs wait. Confirm data
  accessibility (Mongo vs file) the moment the pointer arrives.
- **Metric semantics confusion (C4)** — be precise: fitness/precision characterize *model–log
  agreement*; we interpret them as *team behavioural consistency* only with that caveat stated.
- **`--peer ML` mis-calibration** — venue is ADS; use it only as a stress lens, not the bar.

## Open execution-time forks (I will surface these at the relevant checkpoint, not decide silently)
- **Primary season presentation:** feature one PL season (2021/22 or 2022/23) as the main results and
  use the other as a replication, vs. present both fully. (Phase 2/3 checkpoint.)
- **Team pair for the difference-pitch figure:** which two teams best illustrate the contrast (data-driven). (Phase 2.)
- **Player→process fit-score definition:** RESOLVED 2026-06-04 → **slot-matching + signature-overlap**
  (both: a quantitative overlap score + process-native arc-coverage). Replay-based rejected (too complex).
- **Build-up start:** RESOLVED → **GK-position-based** (first event by the goalkeeper, via `lineups/`).
- **JSON loader:** RESOLVED → **adapt the existing parser** (Option A): replace the Mongo-query block in
  `parse_statsbomb_matches.py` with JSON reads + a field-mapping shim; reuse all downstream code.
- **Player resource:** `create_event_log` must add `resource_key='player_id'` to `format_dataframe`
  (player currently dropped). Safe — does not affect HM discovery.
- **Event types:** RESOLVED → **Pass (30) + Carry (43) + Dribble (14)** in the activity log (add Carry
  to the current [30,14]) — richest zone-to-zone process model; note the event-model change in response-to-referees.
- **Dependency threshold:** RESOLVED → **0.9** (single common threshold for all teams). Per-team sweep
  showed 0.9 dominates the paper's 0.5: half the model size (266 vs 468 transitions → interpretable),
  same fitness/precision, better generalization+simplicity, 3x faster; 0.99 collapses (fitness 0.23).
- **Performance:** per-team discovery parallelized across CPU cores (ProcessPoolExecutor, fork). Precision
  (token ETConformance, ~30s) + generalization (~12s) dominate; teams are independent → parallel.
- **Run scope:** RESOLVED → **primary season 2022/23 (235), all 20 teams**; 2021/22 (108) as replication.
- **Timestamp fix:** event timestamp → `minute*60+second` (period-aware) so event ordering is correct
  (matters for player precede/follow profiles). Pre-existing bug (was `second`-only).
- **Representative players** for the worked profile/fit examples (data-driven choice). (Phase 2.)
- **Container & page-budget decision (post-draft):** after the full draft, breakdown of column cost per
  component → decide 9pp ADS (and what to cut) vs journal vs split. (Post-Phase-3 checkpoint, with options.)
- **Lit-review strands emphasis:** confirm the 3 search strands and how many new refs to integrate. (Phase 1 checkpoint.)

## Open item to resolve at execution start
- **Data load path:** local JSON at `/home/marc/Documents/statsbomb_data/data/` (PL 2021/22 + 2022/23).
  Decide at Phase 2 start: `upload-to-mongo` to reuse the existing Mongo runner, vs. adapt the loader to
  read JSON directly. Confirm StatsBomb open-data schema matches `get_play_actions_statsbomb`
  (native `possession` ids) and the 120×80 → 105×68 standardization (`..._from_statsbomb`).
