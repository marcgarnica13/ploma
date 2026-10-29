# Discipline Cards

Short reference cards naming each discipline's dominant paper-type frequencies, top venues, reproducibility norms, and method conventions. Read by `/research-ideation`, `/interview-me`, and the `editor` agent (in `/review-paper --peer`) when the user gives a `paper_type` or domain hint without specifying a target venue.

**Scope.** This repo ships one card: **applied machine learning / data mining (process mining for sports analytics)**. To add another discipline, copy a card section, fill the fields, and reference the new short-name from `journal-profiles.md` and `methods-referee.md`.

**Maintenance.** When you add a venue profile to `journal-profiles.md`, cross-reference it here. When you add a paper type to `methods-referee.md`, cross-reference it here.

---

## Applied ML / Data Mining (`ml`)

This is the home discipline for this repository: process mining applied to soccer event data, targeting the Springer *Machine Learning* journal.

**Paper-type frequencies (rough share of work at applied-ML / data-mining venues).**

| Type | Share | Notes |
|---|---|---|
| Empirical-ML / computational-pipeline | ~60% | A method + pipeline demonstrated on a dataset (this paper). Dominant mode. The default paper type in `methods-referee.md`. |
| Methods / algorithm | ~20% | A new learning/mining algorithm with theoretical and/or empirical justification. |
| Benchmark / empirical-study | ~10% | Systematic comparison of methods across datasets. |
| Application / case-study | ~10% | A domain application where the ML-general takeaway is the contribution. |

**Dominant venues (shipped in `journal-profiles.md`).** `ML` (Springer *Machine Learning* journal — primary target); `MLCONF` (a selective ML/applied-ML conference/workshop stand-in, matching the paper's previous submission round).

**Reproducibility norms.**
- **Code & data release** expected — a repository with pinned dependencies (`requirements.txt`), run instructions, and the exact data slice. Many venues encourage an artifact/reproducibility badge.
- **Held-out evaluation** is the norm — train/test or cross-validation; reporting only fit-on-train metrics is a red flag.
- **Baselines & ablations** expected to contextualize and isolate the contribution.
- **Caveat for this repo:** the MongoDB data dependency means a fresh checkout cannot fully reproduce results without data access; this must be documented as a reproducibility limitation (see `replication-protocol.md`).

**Method conventions.**
- No significance stars; report metric definitions and N (matches / possessions) in table notes.
- Determinism: fix seeds (or state determinism) for any stochastic discovery / sampling / sweep.
- Code: Python dominant (Python 3.9 here; pm4py / pandas / plotly / floodlight / pymongo). Pin versions.
- Figures: domain-readable (pitch orientation, zone legend) and self-contained.

**Cross-references.** `methods-referee.md` paper types: empirical-ML/computational-pipeline (default), plus the retained reduced-form / structural / theory+empirics / descriptive / formal-theory / survey-experiment for adopters in other fields. `journal-profiles.md`: `ML`, `MLCONF`.

---

## How skills consume these cards

- **`/research-ideation`** — when the user names a topic without a discipline, the skill may infer one from context. The card supplies the default `paper_type` distribution to bias hypothesis generation.
- **`/interview-me`** — the paper-type question uses the card's frequency table to order the option list (most-likely-first per discipline).
- **`editor`** (`/review-paper --peer`) — when the user gives `--peer` without naming a specific venue but with a discipline hint, the editor uses the card's "Dominant venues" list as the candidate set and asks for clarification.

---

## Adding a new discipline card

Copy this template:

```markdown
## [Discipline name] (`short-slug`)

**Paper-type frequencies.**
| Type | Share | Notes |
|---|---|---|
| ... |

**Dominant venues (shipped in `journal-profiles.md`).** [list].

**Reproducibility norms.**
- [release / evaluation / baseline conventions per study type]

**Method conventions.**
- [metric reporting / determinism / dominant code language / figure norms]

**Cross-references.** `methods-referee.md` paper types: [list]. `journal-profiles.md`: [list].
```

Then:

1. Add the card section above (alphabetically by short-slug).
2. Add concrete venue profiles to `journal-profiles.md` for at least the top venues.
3. Add paper types to `methods-referee.md` if your field uses categories not already there.
4. Cross-reference the new short-slug from `/research-ideation` and `/interview-me` if those skills should respect the new defaults.

---

## Where this file lives

- **File:** `.claude/references/discipline-cards.md`
- **Schema parallel:** `.claude/references/journal-profiles.md` (per-venue) and `.claude/references/audit-pet-peeves.md` (living-catalogue format).
- **Consumed by:** `/research-ideation`, `/interview-me`, `editor` agent.
