# Literature Review: Process Mining & Tactic Discovery in Soccer (2023–2026)

**Date:** 2026-06-04
**Query:** Recent (2023–2026) work for the R&R revision — three strands: (1) process mining in sports;
(2) soccer tactic/playing-style discovery incl. graph/GNN/sequence methods (to sharpen the "why PM not
a plain graph" positioning); (3) recent process-discovery/conformance advances. Plus player-level
role/style profiling & player-to-system fit (new featured contribution).

> **Status:** Phase 1 deliverable for the R&R plan (`quality_reports/plans/soft-cooking-seahorse.md`).
> Citations below are split into **VERIFIED** (bibliographic details confirmed against the source) and
> **TO VERIFY** (relevant but not yet fully confirmed — do not cite until checked). CoVe post-flight
> appended at the end.

## Summary

The 2023–2026 literature on football tactics has shifted decisively toward **graph / graph-neural-network
methods** (TacticAI, GoalNet) and **deep representation/clustering** of playing style (Demir et al.
2025), alongside a steady stream of **descriptive playing-style KPI** studies (Plakias et al. 2024) and
**survey consolidation** (Sotudeh 2025 on formation identification). These methods are powerful but
largely **black-box and predictive/evaluative** — they value actions, predict outcomes, or cluster
styles, but they do **not** produce an *interpretable, executable model of how a team builds play* that
can be replayed and conformance-checked.

Crucially for us, **process mining on football is now an actively validated direction**, not a one-off:
Chan et al. (2025) build the first **object-centric event logs** for football. This both legitimises our
approach and marks the modern frontier (object-centricity) we can position against and cite as future
work. None of the 2023–2026 work combines *purpose-driven trace construction + interpretable process
discovery + football-specific heuristic maps + conformance-based regularity + player-level process
profiling* — which is precisely our integrated framework.

On **player-level** analysis, recent work characterises players via **embeddings** (Player Vectors
lineage) or **GNN threat-credit** (GoalNet 2025). These describe *what a player is like* but not *where
the player sits in the team's process*. Our per-player **precede/follow process profile** and
**player→process fit** is a complementary, process-aware and interpretable notion of fit.

## Key Papers (VERIFIED)

### Chan et al. (2025) — Object-centric football event logs *(strand 1; closest neighbour)*
- **Contribution:** First framework to transform football data into **object-centric event logs** (teams,
  players, ball as objects) enhanced with a **spatial dimension**.
- **Venue:** 3rd Workshop on Object-centric Processes from A to Z (OBJECTS 2025) @ BPM 2025. arXiv:2507.12504.
- **Relevance:** Proves PM-on-football is a live 2025 research direction; defines the *object-centric*
  frontier we cite as future work. We differ: they build logs; we discover **interpretable strategy
  models + player profiles** from purpose-driven traces.

### Wang et al. (2024) — TacticAI *(strand 2; the flagship graph method)*
- **Contribution:** GNN assistant for football tactics (corner kicks); predicts receiver/shot and
  generates tactical setups; expert-preferred 90% of the time.
- **Venue:** Nature Communications 15:1906. DOI 10.1038/s41467-024-45965-x. Data: 7,176 corners.
- **Relevance:** The headline 2024 *graph* approach — exactly the "why not a graph?" comparator. Powerful
  but **black-box and corner-kick-scoped**; no interpretable, replayable open-play strategy model.

### Jiang et al. (2025) — GoalNet *(strands 2 & player-level)*
- **Contribution:** GNN that assigns **individual credit for expected-threat change** from event-centric
  spatio-temporal graphs; surfaces overlooked defenders/midfielders.
- **Venue:** arXiv:2503.09737.
- **Relevance:** State-of-the-art *player* evaluation via graphs — but a scalar/credit view, not a
  process-position profile. Contrast for our interpretable precede/follow player profile.

### Demir, Şahin & Üre (2025) — Deep Embedded Clustering of playing styles *(strand 2)*
- **Contribution:** DEC over large-scale event data segmented into 4 phases of play → team playing-style
  clusters; features include pass motifs, positional tendencies, graph metrics.
- **Venue:** *Sports Analytics* (Springer), eds. Dong, Sun, Xie, Jiang. DOI 10.1007/978-3-032-06167-6_4.
- **Relevance:** Recent *style discovery* — but clustering yields style *labels*, not an executable
  process model. Reinforces "interpretable process model" as our differentiator.

### Plakias et al. (2024) — Playing styles as KPIs *(strand 2; descriptive)*
- **Contribution:** 16 tactical dimensions (possession vs direct, high vs deep press) predicting match
  outcome; **5,992 team observations, 11 European leagues, 2021–22**.
- **Venue:** J. Functional Morphology and Kinesiology 9(2):88. DOI 10.3390/jfmk9020088.
- **Relevance:** Recent evidence that *style* matters and is measurable from aggregates — motivates the
  need for *sequence-/process-level* models like ours. Note: same 2021–22 era as our new data.

### Sotudeh (2025) — Formation identification survey *(strand 2; related-work anchor)*
- **Contribution:** Two-decade survey of team-/position-level **formation identification** from event &
  tracking data; preprocessing, methods, limitations.
- **Venue:** Frontiers in Sports and Active Living 6:1512386. DOI 10.3389/fspor.2024.1512386.
- **Relevance:** Up-to-date related-work scaffold; situates formation/style work and its gaps (our
  process angle is absent from it).

### Berti et al. (2024) — OCEL 2.0 *(strand 3; modern PM methodology)*
- **Contribution:** The **object-centric event log 2.0** standard (object change, relationships, qualified
  relations; SQLite/XML/JSON).
- **Venue:** OCEL 2.0 specification, arXiv:2403.01975 (v1 March 2024). *[CoVe: cite as 2024; the "Oct
  2023 release" detail is unconfirmed by the arXiv record.]*
- **Relevance:** The recent PM-methodology direction; pairs with Chan (2025) to frame our future-work
  (object-centric extension of our single-case purpose traces).

### Decroos & Davis (2019) — Player Vectors *(player-level background; CoVe-verified)*
- **Contribution:** Characterizes players' **playing style** as vectors learned from match-event streams.
- **Venue:** ECML-PKDD 2019, LNCS 11908; DOI 10.1007/978-3-030-46133-1_34 (proceedings year 2020).
- **Relevance:** Canonical *player-style-from-events* baseline. Black-box embedding — contrast for our
  interpretable process-position profile.

### Aalbers & Van Haaren (2019) — Distinguishing player roles *(player-level background; CoVe-verified)*
- **Contribution:** Identifies player **roles** from play-by-play event data.
- **Venue:** Machine Learning and Data Mining for Sports Analytics 2019, Springer; DOI
  10.1007/978-3-030-17274-9_3 (arXiv:1809.05173, 2018). **Authors: Bart Aalbers, Jan Van Haaren** (CoVe-corrected).
- **Relevance:** Role-level player characterization predecessor; our process-position profile is complementary.

## TO VERIFY (relevant; confirm before citing — see CoVe queue)
- **AI in soccer tactical analysis — narrative review (Jan 2025).** Recent review for intro framing;
  exact authors/venue unconfirmed.
- **van Haaren et al. (eds., 2025) — MLSA 2024 proceedings**, Springer LNCS 10.1007/978-3-031-86692-0.
  Venue/context citation.
- **Passing-path → shooting outcome**, Nature Scientific Reports 2024 (s41598-024-60183-7). Sequence-level
  analysis; authors unconfirmed.

## Thematic Organization

**Methodological innovations (2023–26):** graph/GNN for tactics & player value (Wang 2024; Jiang 2025);
deep embedded clustering for style (Demir 2025); object-centric logs for football (Chan 2025); OCEL 2.0
standard (Berti 2023).

**Empirical/descriptive:** style-as-KPI across 11 leagues (Plakias 2024); formation-ID survey (Sotudeh 2025).

**Open debates relevant to us:**
1. *Interpretability vs predictive power* — GNNs win on prediction but lose on transparent, executable
   strategy artifacts. Our conformance-checkable process model + heuristic maps sits on the interpretable side.
2. *Object-centric vs single-case* — Chan (2025)/Berti (2023) push object-centric; our single-case
   purpose-trace abstraction is simpler and discovery-ready, with object-centricity as a clear extension.
3. *Player representation* — embedding/credit (black-box) vs process-position (interpretable). Open space
   our player→process profile occupies.

## Positioning note (the "why process mining, not a graph?" argument — for C2/§1–§2)

1. **A directly-follows / attributed graph (and even a GNN on an event graph) captures pairwise or
   aggregate relations, not an end-to-end process.** The Heuristic Miner's **dependency measure** filters
   noise/low-frequency behaviour and yields a model with **concurrency and causal structure** that a raw
   DFG does not. (Methodological cites already in bib: Weijters 2006; Buijs 2014; Syring 2019.)
2. **A process model is *executable and conformance-checkable*.** We can *replay* possessions and measure
   **fitness/precision/generalization** — semantics a static graph/embedding does not provide. This is the
   backbone of our evaluation (and the new precision/simplicity columns).
3. **Interpretability for practitioners.** Against black-box GNNs (TacticAI 2024, GoalNet 2025), our
   heuristic maps are directly readable by analysts — the integrated-framework selling point.
4. **Empirical leg (DFG baseline):** we instantiate the "plain graph" (a DFG) and show it under-models the
   structure HM recovers — answering R1's challenge *with evidence*, not just argument.
5. **Live, validated direction:** Chan (2025) shows PM-on-football is current; we extend from *log
   construction* to *purpose-driven discovery + interpretable maps + regularity + player profiling*.

## Gaps & Opportunities (what we exploit)
1. No 2023–26 method couples **purpose-driven trace construction** with **interpretable process discovery**
   for team strategy — recent work is GNN/clustering (black-box) or descriptive KPIs.
2. **Player-to-system fit** is recognised as important (embedding/recruitment work) but **not modelled at
   the process level** — our precede/follow profile + fit is novel and interpretable.
3. **Object-centricity** (Chan 2025; OCEL 2.0) is the natural future extension to cite — strengthens the
   discussion without expanding this paper's scope.

## Suggested Next Steps
- Integrate the 7 VERIFIED entries into `manuscript/mybib.bib`; weave into §1 (why-PM + GNN contrast),
  §2 (related work: graph/clustering/PM-football + formation survey), Discussion (object-centric future
  work), and the player section (GoalNet/Player-Vectors contrast).
- Run `/validate-bib --semantic` to DOI-verify all new keys (esp. the TO-VERIFY queue) before drafting.
- Confirm the two player-style references (Player Vectors; roles paper) — load-bearing for the player
  contribution.

## BibTeX Entries (VERIFIED — ready to add to mybib.bib after `/validate-bib`)

```bibtex
@misc{Chan2025,
  author = {Vito Chan and Lennart Ebert and Paul-Julius Hillmann and Christoffer Rubensson and Stephan A. Fahrenkrog-Petersen and Jan Mendling},
  title  = {Transforming Football Data into Object-centric Event Logs with Spatial Context Information},
  year   = {2025},
  note   = {3rd Workshop on Object-centric Processes from A to Z (OBJECTS 2025) @ BPM 2025},
  doi    = {10.48550/arXiv.2507.12504},
}

@Article{Wang2024,
  author  = {Zhe Wang and Petar Veli{\v{c}}kovi{\'c} and Daniel Hennes and Nenad Toma{\v{s}}ev and Laurel Prince and Michael Kaisers and Yoram Bachrach and Romuald Elie and Li Kevin Wenliang and Federico Piccinini and William Spearman and Ian Graham and Jerome Connor and Yi Yang and Adri{\`a} Recasens and Mina Khan and Nathalie Beauguerlange and Pablo Sprechmann and Pol Moreno and Nicolas Heess and Michael Bowling and Demis Hassabis and Karl Tuyls},
  title   = {{TacticAI}: an {AI} assistant for football tactics},
  journal = {Nature Communications},
  volume  = {15},
  number  = {1},
  pages   = {1906},
  year    = {2024},
  doi     = {10.1038/s41467-024-45965-x},
}

@misc{Jiang2025,
  author = {Jacky Hao Jiang and Jerry Cai and Anastasios Kyrillidis},
  title  = {Unveiling Hidden Pivotal Players with {GoalNet}: A {GNN}-Based Soccer Player Evaluation System},
  year   = {2025},
  doi    = {10.48550/arXiv.2503.09737},
}

@InCollection{Demir2025,
  author    = {Ege Demir and Yusuf H. {\c{S}}ahin and Naz{\i}m Kemal {\"U}re},
  title     = {How Do Football Teams Play? A Deep Embedded Clustering Approach to Reveal Playing Styles},
  booktitle = {Sports Analytics},
  series    = {Lecture Notes in Computer Science},
  publisher = {Springer Nature Switzerland},
  year      = {2025},
  doi       = {10.1007/978-3-032-06167-6\_4},
}

@Article{Plakias2024,
  author  = {Spyridon Plakias and Themistoklis Tsatalas and Vasileios Armatas and Dimitris Tsaopoulos and Giannis Giakas},
  title   = {Tactical Situations and Playing Styles as Key Performance Indicators in Soccer},
  journal = {Journal of Functional Morphology and Kinesiology},
  volume  = {9},
  number  = {2},
  pages   = {88},
  year    = {2024},
  doi     = {10.3390/jfmk9020088},
}

@Article{Sotudeh2024,
  author  = {Hadi Sotudeh},
  title   = {The principles of tactical formation identification in association football (soccer) -- a survey},
  journal = {Frontiers in Sports and Active Living},
  volume  = {6},
  pages   = {1512386},
  year    = {2024},
  doi     = {10.3389/fspor.2024.1512386},
}

@misc{Berti2024,
  author = {Alessandro Berti and Istv{\'a}n Koren and Jan Niklas Adams and Gyunam Park and Benedikt Knopp and Nina Graves and Majid Rafiei and Lukas Li{\ss} and Leah Tacke Genannt Unterberg and Yisong Zhang and Christopher Schwanen and Marco Pegoraro and Wil M. P. van der Aalst},
  title  = {{OCEL} ({Object-Centric Event Log}) 2.0 Specification},
  year   = {2024},
  doi    = {10.48550/arXiv.2403.01975},
}

@InCollection{Decroos2019pv,
  author    = {Tom Decroos and Jesse Davis},
  title     = {Player Vectors: Characterizing Soccer Players' Playing Style from Match Event Streams},
  booktitle = {Machine Learning and Knowledge Discovery in Databases (ECML PKDD 2019)},
  publisher = {Springer International Publishing},
  year      = {2020},
  doi       = {10.1007/978-3-030-46133-1\_34},
}

@InCollection{Aalbers2019,
  author    = {Bart Aalbers and Jan Van Haaren},
  title     = {Distinguishing Between Roles of Football Players in Play-by-Play Match Event Data},
  booktitle = {Machine Learning and Data Mining for Sports Analytics},
  publisher = {Springer International Publishing},
  year      = {2019},
  doi       = {10.1007/978-3-030-17274-9\_3},
}
```

---

<details>
<summary>✅ Post-Flight Verification (CoVe) — PASS (with corrections applied)</summary>

Independent `claim-verifier` (forked context, never saw this draft) checked 9 bibliographic + 1 factual
claim against Crossref / arXiv / publisher pages. **9/10 SUPPORTED; 1 premise CONTRADICTED — corrected.**

- **CORRECTED — roles paper authors:** Bart **Aalbers** & Jan **Van Haaren** (not as first drafted).
- **CORRECTED — OCEL 2.0 year → 2024** (arXiv v1 4 Mar 2024); "Oct 2023 release" unverified, removed.
- **NUANCE — Sotudeh survey:** cite year **2024** (volume 6); online Feb 2025. Set to 2024.
- **NUANCE — Player Vectors:** DOI 10.1007/978-3-030-46133-1_34; proceedings year 2020 (ECML-PKDD 2019).
- **VERIFIED:** Chan 2025, Wang 2024 (TacticAI, Nat. Comm. 15:1906), Jiang 2025 (GoalNet), Demir 2025
  (LNCS; full names Ege Demir, Yusuf H. Şahin, Nazım Kemal Üre), Plakias 2024.
- **FACTUAL VERIFIED:** TacticAI's core model is a GNN; experts preferred its suggestion in 45/50 (90%) cases.

All corrections are reflected in the entries above. Re-run `/validate-bib --semantic` after pasting into
`mybib.bib` as the final DOI gate.
</details>
