<!-- Adapted from Hugo Sant'Anna's clo-author (github.com/hugosantanna/clo-author),
     used with permission. Journal-calibration schema credit: Hugo Sant'Anna. -->

# Journal Profiles

Calibration data for the `/review-paper --peer [journal]` simulated peer-review pipeline. Each profile tells the editor how to select referees (disposition-pool weights), what concerns that journal typically emphasizes, and any journal-specific formatting conventions.

**How this file is used.** The `editor` agent reads this file before each `--peer` run, picks the requested `[journal]`, and uses its Referee-pool weights + Typical concerns to select two referees with different dispositions and to seed their pet-peeve priors.

**Customizing for your field.** This file ships with profiles relevant to **applied machine-learning / sports-analytics** work, targeting the Springer *Machine Learning* journal as the primary venue. To add another venue (a different ML journal, a conference, a domain venue), copy the [Field adaptation](#field-adaptation) template at the bottom into a new section and reference it by the short name you define.

---

## Schema

Every profile has these fields:

- **Short name** — the string you pass to `--peer [name]` (e.g., `ML`).
- **Focus** — what the venue publishes; what it doesn't.
- **Bar** — what it takes to clear the desk; typical acceptance rate context.
- **Domain-referee adjustments** — how the substance referee should re-weight their dimensions for this venue (e.g., "Contribution & Novelty 30 → 35, Literature Positioning 25 → 30").
- **Methods-referee adjustments** — how the methods referee should re-weight for this venue (e.g., "Evaluation validity 30 → 35, Reproducibility 10 → 15").
- **Typical concerns** — 3–5 direct-quote questions a referee at this venue will ask.
- **Referee-pool weights** — probability weights over the 6 dispositions (METHODOLOGY/RIGOR / REPRODUCIBILITY / NOVELTY/RELATED-WORK / EVALUATION/VALIDITY / CLARITY/PRESENTATION / SKEPTIC). Editor draws two *different* dispositions from this distribution.
- **Table format override** (optional) — any venue-specific formatting rule.

The 6 dispositions map onto how the `domain-referee` and `methods-referee` agents read a paper; keep
the FATAL / ADDRESSABLE / TASTE classification and the editor-synthesis machinery (see
`.claude/agents/editor.md`) unchanged when adding profiles.

---

## Machine-Learning venues

### Springer Machine Learning journal (ML)

**Short name:** `ML`

**Focus.** Springer's *Machine Learning* journal publishes original research on machine-learning
methods and their applications: learning algorithms, empirical-systems and applied-ML papers,
data-mining / process-mining methods, and well-evaluated applications to a real domain (here, soccer
event data). It values **sound method + honest, generalizable evaluation + reproducibility** over a
single flashy benchmark number. Application papers are welcome when the method or the empirical
finding is of general ML interest, not only domain-specific.

**Bar.** A clear methodological or empirical contribution that an ML reader (not only a sports
analyst) would learn from. The evaluation must be honest about generalization; the work should be
reproducible (released code/data, pinned dependencies) or the limits to reproducibility must be
stated plainly. Pure domain reporting with no ML-general takeaway tends to be redirected to a domain
venue.

**Domain-referee adjustments.**
- Contribution & Novelty 30 → 35 (the ML-general takeaway must be crisp)
- Literature Positioning 25 → 30 (must cover both ML/process-mining and sports-analytics prior work, and the delta over any previous conference version)
- Fit for Target Journal 10 → 5 (ML publishes broadly across method+application; fit is rarely binding)

**Methods-referee adjustments.**
- Evaluation validity 30 → 35 (held-out / cross-validated evidence is load-bearing; fit-on-train metrics do not support generalization)
- Reproducibility 10 → 15 (released code/data + pinned deps expected; the MongoDB dependency is a documented caveat)
- Baselines & ablations 20 → 20 (unchanged — still required)

**Typical concerns.**
- "Is the method sound, and are the modeling choices (segmentation, the 24-zone abstraction, the `action##zone` activity key, heuristic-net discovery) justified rather than arbitrary?"
- "Is the headline metric evaluated on held-out data, or only on the data the model was discovered from? Where is the baseline?"
- "Does this generalize beyond this one dataset — other seasons, competitions, or data providers (Wyscout vs StatsBomb)?"
- "Is the related work complete across BOTH process mining / data mining AND sports analytics, and is the contribution over the previous conference version clear?"
- "Can a reader reproduce this — code, data access, pinned dependencies, run instructions?"
- "What does the ML community learn here that transfers beyond soccer?"

**Referee-pool weights.**
- EVALUATION/VALIDITY: 0.25
- METHODOLOGY/RIGOR: 0.20
- REPRODUCIBILITY: 0.20
- NOVELTY/RELATED-WORK: 0.15
- SKEPTIC: 0.10
- CLARITY/PRESENTATION: 0.10

**Table format override.** No significance stars required; report metric definitions and N
(matches / possessions) in table notes. Figures must state pitch orientation and zone legend.

---

### ML conference / workshop track (MLCONF)

**Short name:** `MLCONF`

**Focus.** A stand-in profile for a selective ML or applied-ML conference / workshop (e.g., the kind
of venue the paper's *previous* submission targeted — see `review/review1–3.md`). Shorter format,
faster turnaround, novelty- and presentation-weighted relative to the journal. Use this profile to
stress-test the paper against the lighter, novelty-first reviewing style before the journal
resubmission.

**Bar.** A crisp, novel idea with a credible (if not exhaustive) evaluation. Conference reviewers
reward a clear contribution and a clean demo over comprehensive ablations; they are less forgiving of
unclear writing in a tight page budget.

**Domain-referee adjustments.**
- Contribution & Novelty 30 → 35 (novelty-first reviewing)
- External Validity / Scope 15 → 10 (conferences tolerate narrower scope)

**Methods-referee adjustments.**
- Evaluation validity 30 → 30 (unchanged; still must not be fit-on-train)
- Baselines & ablations 20 → 25 (a single baseline comparison is the minimum bar)
- Reproducibility 10 → 5 (encouraged, less strictly enforced than the journal)

**Typical concerns.**
- "What is the single new idea here, in one sentence?"
- "Is there at least one baseline, and does the method beat it?"
- "Is the paper readable within the page budget — is the contribution clear by the end of the intro?"
- "Is the evaluation enough to believe the claim, even if not exhaustive?"

**Referee-pool weights.**
- NOVELTY/RELATED-WORK: 0.30
- EVALUATION/VALIDITY: 0.20
- CLARITY/PRESENTATION: 0.20
- METHODOLOGY/RIGOR: 0.15
- SKEPTIC: 0.10
- REPRODUCIBILITY: 0.05

**Table format override.** None specific; respect the page budget — tables must earn their space.

---

## Field adaptation

The profiles above target ML venues. The **pipeline is field-agnostic** — nothing in `editor.md`,
`domain-referee.md`, or `methods-referee.md` hard-codes a field. What varies by venue is the journal
profile and the disposition weights.

**To adapt for a different venue:**

1. Add a new section below using `### Venue Name (SHORT)`.
2. Fill each schema field:
   - **Focus** — what the venue publishes (look at the last 6–12 months of accepted papers).
   - **Bar** — acceptance-rate context + one sentence on what the editor/PC is looking for.
   - **Domain-referee adjustments** — re-weight Contribution / Lit-positioning / Substance / External-validity / Fit for this venue's taste.
   - **Methods-referee adjustments** — re-weight the methods dimensions (for the empirical-ML paper type: Method soundness / Evaluation validity / Baselines & ablations / Generalization / Reproducibility). If the venue prefers a different paper-type taxonomy, edit `methods-referee.md` accordingly.
   - **Typical concerns** — read 2–3 recent reviews (many ML venues publish reviews via OpenReview) and distill 3–5 recurring referee questions.
   - **Referee-pool weights** — the 6 dispositions (METHODOLOGY/RIGOR, REPRODUCIBILITY, NOVELTY/RELATED-WORK, EVALUATION/VALIDITY, CLARITY/PRESENTATION, SKEPTIC) are general enough for any ML venue. Re-weight based on what that venue's reviewers actually ask about. Weights must sum to 1.0.
   - **Table format** — any venue-specific conventions.

**Profile template (copy and fill):**

```markdown
### Venue Name (SHORT)

**Short name:** `SHORT`
**Focus.** ...
**Bar.** ...
**Domain-referee adjustments.**
- Dimension X → Y (reason)
**Methods-referee adjustments.**
- Dimension X → Y (reason)
**Typical concerns.**
- "..."
**Referee-pool weights.**
- METHODOLOGY/RIGOR: 0.xx
- REPRODUCIBILITY: 0.xx
- NOVELTY/RELATED-WORK: 0.xx
- EVALUATION/VALIDITY: 0.xx
- CLARITY/PRESENTATION: 0.xx
- SKEPTIC: 0.xx
**Table format override.** ...
```

**Examples for venues we don't yet ship** (to be filled in by adopters):

- `### JMLR` — methods-first, theory-friendly, strict on reproducibility. Weights: METHODOLOGY/RIGOR high, REPRODUCIBILITY high.
- `### Data Mining and Knowledge Discovery (DAMI)` — data-mining / pattern-mining methods + applications. Weights: METHODOLOGY/RIGOR high, EVALUATION/VALIDITY high.
- `### NeurIPS / ICML (main track)` — high-novelty, benchmark-heavy. Weights: NOVELTY/RELATED-WORK high, EVALUATION/VALIDITY high, SKEPTIC medium.

---

## Cross-references

- `.claude/agents/editor.md` — reads this file.
- `.claude/agents/domain-referee.md` — applies domain-referee adjustments.
- `.claude/agents/methods-referee.md` — applies methods-referee adjustments.
- `.claude/skills/review-paper/SKILL.md` — `--peer [journal]` mode entry point.
