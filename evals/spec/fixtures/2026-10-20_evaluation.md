# Decision log: evaluation

**Date:** 2026-10-20
**Input:** sections/results.tex
**Status:** complete

## Summary

| ID | Decision | Answer | Lens |
|---|---|---|---|
| D1 | Headline comparison | Report both baselines in the main table | Empiricist |
| D2 | Scope of the claim | Claim one season only; no generalization claim | Theorist |

## Settled by the repo

| Decision | Answer | Evidence |
|---|---|---|
| Headline metric | average fitness 0.81 | results/metrics.json:avg_fitness |

## Decisions

### D1: Headline comparison
**Lens:** Empiricist
**Question:** The results table compares the method with a win-ratio and a rating-update baseline (sections/results.tex:15-16). Keep both in the main table?
**Options:**
1. Keep both baselines in the main table (Recommended): a single baseline invites the question of whether a simpler method already reaches the score.
2. Keep only the stronger baseline: saves a row, loses the naive reference point.
**Answer:** Keep both baselines in the main table
**Rationale:** a single baseline invites the question of whether a simpler method already reaches the score.
**Consequences:** the results section keeps a three-row table.

### D2: Scope of the claim
**Lens:** Theorist
**Question:** The data cover one season (main.tex:15). Claim generalization across seasons, or scope the claim to one season?
**Options:**
1. Scope the claim to one season (Recommended): no second season is in the results, so a broader claim has no evidence.
2. Claim generalization: needs a second season of data first.
**Answer:** Scope the claim to one season
**Rationale:** no second season is in the results.
**Consequences:** the abstract and introduction say "one season"; a second season is future work.

## Open

- None.
