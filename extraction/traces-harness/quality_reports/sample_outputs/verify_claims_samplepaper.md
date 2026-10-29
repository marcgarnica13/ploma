# Claim Verification (CoVe): manuscript/samplepaper.tex

**Date:** 2026-06-04 (full-audit). Method: fresh-context `claim-verifier` (never saw the draft);
each literature claim checked against the actual cited work via web sources.

## Result: PASS — 8/8 literature claims SUPPORTED, 0 contradicted.

| # | Claim (related work) | Verdict | Source |
|---|---|---|---|
| 1 | TacticAI = GNN to predict & generate corner-kick tactics | SUPPORTED | Wang et al., Nat. Commun. 2024 / arXiv:2310.10553 |
| 2 | GoalNet values players from event-centric graphs | SUPPORTED | Jiang et al., arXiv:2503.09737 |
| 3 | Deep embedded clustering → team playing styles from large event sets | SUPPORTED | Demir et al. 2025, doi 10.1007/978-3-032-06167-6_4 |
| 4 | Chan et al. = object-centric/process-mining football model, readable/replayable | SUPPORTED | Chan et al., arXiv:2507.12504 |
| 5 | Bekkers & Dabadghao extend Gyarmati passing motifs; motifs lack spatiotemporal info | SUPPORTED | JSA 2019, doi 10.3233/JSA-190290 |
| 6 | Kröckel & Bodendorf: end-to-end PM on a small sample | SUPPORTED | Front. AI 2020, doi 10.3389/frai.2020.00047 |
| 7 | Hewitt et al. playing-style definition (quoted verbatim) | SUPPORTED | Hewitt et al. 2016, doi 10.1080/24748668.2016.11868892 |
| 8 | Davis et al.: sports analytics in 3 areas (recruitment / match prep / health) | SUPPORTED (substance) | Davis et al., Machine Learning 2024, doi 10.1007/s10994-024-06585-0 |

## Advisory (LOW, non-gating)

- **`Davis202207` venue/year:** the bib entry is the IJCAI-2022 *workshop* paper ("Evaluating Sports
  Analytics Models…", 2022). The "three areas" division was verified verbatim in the **Davis et al.
  2024 Machine Learning journal** paper ("Methodology and evaluation in sports analytics"). Confirm the
  2022 workshop paper makes the same three-area division; if not, cite the 2024 journal paper for that
  sentence (§1). Substance is correct either way.

## Internal-consistency claims (flagged by proofread, not literature-CoVe)

- **"19 of 20 teams"** (abstract) is not restated in the body/Table — add to §5.2 for traceability.
- **"replicated on 2021/2022"** (abstract) is not presented in the body — add one sentence (the 108
  results exist) or soften. These are reproducibility/traceability items (deselected from this audit),
  surfaced here for completeness.

No literature claim misrepresents its source.
