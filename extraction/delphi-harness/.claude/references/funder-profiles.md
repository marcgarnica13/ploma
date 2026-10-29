<!-- Adapted from Hugo Sant'Anna's clo-author (github.com/hugosantanna/clo-author),
     used with permission. Panel-calibration schema credit: Hugo Sant'Anna. -->

# Funder Profiles

Calibration data for the `/review-proposal --panel [funder]` simulated panel-review pipeline. Each profile tells the program officer how to select panelists (disposition-pool weights), what concerns that funder typically emphasizes, and any funder-specific formatting conventions.

**How this file is used.** The `editor` (program-officer) agent reads this file before each `--panel` run, picks the requested `[funder]`, and uses its Panelist-pool weights + Typical concerns to select two panelists with different dispositions and to seed their pet-peeve priors.

**Customizing for your funder.** This file ships with one **GENERIC scientific grant proposal** profile (the default) plus three **STUB** profiles ready to fill — **NIH**, **NSF**, and **ERC**. To add another funder (a specific foundation, agency, or program), copy the [Field adaptation](#field-adaptation) template at the bottom into a new section and reference it by the short name you define.

---

## Schema

Every profile has these fields:

- **Short name** — the string you pass to `--panel [name]` (e.g., `GENERIC`).
- **Focus** — what the funder supports; what it doesn't.
- **Bar** — what it takes to clear the desk (program-officer triage); typical funding-rate context.
- **Domain-referee adjustments** — how the substance panelist should re-weight their dimensions for this funder (e.g., "Significance 30 → 35, Related Work / Prior Art 25 → 30").
- **Methods-referee adjustments** — how the methodology panelist should re-weight for this funder (e.g., "Approach & Feasibility 30 → 35, Funder Fit & Compliance 10 → 15").
- **Typical concerns** — 3–5 direct-quote questions a panelist at this funder will ask.
- **Panelist-pool weights** — probability weights over the 6 dispositions (SIGNIFICANCE / INNOVATION / APPROACH-FEASIBILITY / TEAM-INVESTIGATORS / BROADER-IMPACT / SKEPTIC). Program officer draws two *different* dispositions from this distribution.
- **Desk-reject / decline criteria** (optional) — funder-specific triage signals that send a proposal back without panel review.
- **Table format override** (optional) — any funder-specific formatting rule (page limits, required sections).

The 6 dispositions map onto how the `domain-referee` and `methods-referee` agents read a proposal; keep
the FATAL / ADDRESSABLE / TASTE classification and the program-officer-synthesis machinery (see
`.claude/agents/editor.md`) unchanged when adding profiles.

---

## Generic scientific grant proposal (GENERIC) — DEFAULT

**Short name:** `GENERIC`

**Focus.** A funder-agnostic scientific grant program supporting investigator-initiated research
proposals. It values a **significant problem + a sound, feasible approach + a qualified team + a
credible plan for broader impact**. The proposal must convince a non-specialist panel that the work
matters, that it can be done with the requested resources in the requested time, and that the
investigators are the right people to do it.

**Bar.** A clear, important research problem; a method that is both innovative and feasible; a
realistic budget and timeline; and a team with the track record and environment to deliver. Vague
aims, a method that cannot be executed by the proposed team in the proposed window, or a proposal
that ignores the funder's stated priorities tends to be declined or returned without review.

**Domain-referee adjustments.** None for the generic profile (use the default 6-dimension weights).

**Methods-referee adjustments.** None for the generic profile (use the default grant-proposal weights).

**Typical concerns.**
- "Is the problem significant — would solving it move the field, and is the gap clearly stated?"
- "Is the approach both novel and feasible — can this team execute it with the requested resources in the proposed timeline?"
- "Are the aims independent enough that failure of one does not sink the whole project?"
- "Does the team have the track record, preliminary evidence, and environment to deliver?"
- "Is there a credible, concrete broader-impact / dissemination plan, not a boilerplate paragraph?"
- "Does the proposal fit this funder's stated mission and comply with its format and eligibility rules?"

**Panelist-pool weights.**
- APPROACH-FEASIBILITY: 0.25
- SIGNIFICANCE: 0.20
- INNOVATION: 0.20
- TEAM-INVESTIGATORS: 0.15
- BROADER-IMPACT: 0.10
- SKEPTIC: 0.10

**Desk-reject / decline criteria.** Out-of-scope topic; no clear gap or significance; budget or
timeline obviously infeasible for the proposed work; missing required sections; over the page limit.

**Table format override.** Report a timeline (Gantt or milestone table) and a budget summary. Figures
must be self-contained with a caption stating what each panel shows.

---

## NIH (NIH) — STUB: TODO calibrate

**Short name:** `NIH`

**Focus.** *(STUB — fill from the relevant NIH Institute/Center and FOA.)* Biomedical and health
research. Mechanism-dependent: **R01** (mature, hypothesis-driven, larger scope) vs **R21**
(exploratory / high-risk, no strong preliminary data required, capped budget and duration). State the
mechanism in the panel call.

**Bar.** *(TODO: calibrate.)* NIH scores on five core criteria — **Significance, Innovation,
Approach, Investigators, Environment** — each scored 1 (exceptional) to 9 (poor), rolled into an
Overall Impact score. The Approach criterion is usually the most discriminating.

**Domain-referee adjustments.** *(TODO: calibrate.)* Map: Significance → Significance criterion;
Related Work / Prior Art and Innovation → Innovation criterion; Funder-Priority Alignment →
Institute/Center mission fit.

**Methods-referee adjustments.** *(TODO: calibrate.)* Weight **Approach & Feasibility** heavily (the
Approach criterion drives most fundable/not-fundable splits); fold rigor-and-reproducibility and the
Vertebrate Animals / Human Subjects / Inclusion-plan checks into Funder Fit & Compliance.

**Typical concerns.** *(TODO: calibrate with real study-section language.)*
- "Significance: does the project address an important problem or a critical barrier to progress?"
- "Innovation: does it challenge current paradigms or use novel concepts/methods?"
- "Approach: is the strategy well-reasoned, with rigor, feasible aims, and alternative strategies for pitfalls?"
- "Investigators / Environment: is the team and institutional setting suited to the work?"

**Panelist-pool weights.** *(TODO: calibrate — placeholder mirrors GENERIC.)*
- APPROACH-FEASIBILITY: 0.30
- SIGNIFICANCE: 0.20
- INNOVATION: 0.15
- TEAM-INVESTIGATORS: 0.15
- BROADER-IMPACT: 0.10
- SKEPTIC: 0.10

**Desk-reject / decline criteria.** *(TODO.)* Non-responsive to the FOA; missing required components
(Specific Aims, rigor, resource-sharing plan); over page limits.

**Table format override.** *(TODO.)* One-page Specific Aims; page limits per mechanism (R01 12 pp
Research Strategy, R21 6 pp). Confirm against the active FOA.

---

## NSF (NSF) — STUB: TODO calibrate

**Short name:** `NSF`

**Focus.** *(STUB — fill from the relevant NSF directorate/division and solicitation.)* Fundamental
research and education across science and engineering. Reviewed against **two coequal merit-review
criteria: Intellectual Merit and Broader Impacts.**

**Bar.** *(TODO: calibrate.)* Both criteria must be addressed substantively. A strong Intellectual
Merit case with a boilerplate Broader Impacts section is a common decline reason.

**Domain-referee adjustments.** *(TODO: calibrate.)* Map: Significance + Innovation + Approach →
**Intellectual Merit**; Broader Impact → **Broader Impacts** (treat as a first-class, separately
scored criterion, not an afterthought).

**Methods-referee adjustments.** *(TODO: calibrate.)* Weight Approach & Feasibility and the
Broader-Impacts plan; fold data-management-plan and results-of-prior-NSF-support checks into Funder
Fit & Compliance.

**Typical concerns.** *(TODO: calibrate with real panel-summary language.)*
- "Intellectual Merit: what is the potential to advance knowledge, and is the plan sound?"
- "Broader Impacts: what is the potential to benefit society — education, broadening participation, infrastructure?"
- "Are both criteria addressed with specific, assessable activities (not aspirations)?"

**Panelist-pool weights.** *(TODO: calibrate — placeholder mirrors GENERIC.)*
- APPROACH-FEASIBILITY: 0.25
- SIGNIFICANCE: 0.20
- INNOVATION: 0.15
- BROADER-IMPACT: 0.20
- TEAM-INVESTIGATORS: 0.10
- SKEPTIC: 0.10

**Desk-reject / decline criteria.** *(TODO.)* Missing Broader Impacts statement; missing
Data Management Plan; non-compliant with the PAPPG / solicitation format.

**Table format override.** *(TODO.)* 15-page Project Description (confirm against solicitation);
separate, clearly labeled Intellectual Merit and Broader Impacts treatment.

---

## ERC (ERC) — STUB: TODO calibrate

**Short name:** `ERC`

**Focus.** *(STUB — fill from the active Horizon Europe ERC work programme.)* Frontier, investigator-
driven research selected on **scientific excellence as the sole criterion**, evaluated through three
elements: **Excellence (of the project and the PI), Impact, and Quality and Efficiency of the
Implementation.** Grant types: Starting / Consolidator / Advanced (PI-career-stage dependent).

**Bar.** *(TODO: calibrate.)* High-risk / high-gain, ground-breaking ambition. The PI's track record
and the feasibility of the (often single-PI) project are weighted heavily. State the grant type in
the panel call.

**Domain-referee adjustments.** *(TODO: calibrate.)* Map: Significance + Innovation → **Excellence
(ground-breaking nature, ambition)**; Scope & Transferability + Broader Impact → **Impact**.

**Methods-referee adjustments.** *(TODO: calibrate.)* Weight Approach & Feasibility and Team /
Investigators toward the **Implementation** and **PI track-record** elements; fold
host-institution-commitment and ethics checks into Funder Fit & Compliance.

**Typical concerns.** *(TODO: calibrate with real ERC panel language.)*
- "Excellence: is the project ground-breaking, ambitious, and feasible? Is the PI's track record exceptional for their career stage?"
- "Impact: would success have a substantial impact on the field or beyond?"
- "Implementation: is the methodology sound, the timeline realistic, and the host environment adequate?"

**Panelist-pool weights.** *(TODO: calibrate — placeholder mirrors GENERIC.)*
- INNOVATION: 0.25
- APPROACH-FEASIBILITY: 0.20
- SIGNIFICANCE: 0.20
- TEAM-INVESTIGATORS: 0.20
- BROADER-IMPACT: 0.05
- SKEPTIC: 0.10

**Desk-reject / decline criteria.** *(TODO.)* PI eligibility window (years-since-PhD) not met;
over page limits (B1 / B2 structure); host-institution support letter missing.

**Table format override.** *(TODO.)* Two-part proposal (B1 extended synopsis + B2 full); confirm
page limits and the PI track-record / 10-publications format against the active work programme.

---

## Field adaptation

The profiles above span generic + three major funders. The **pipeline is funder-agnostic** — nothing
in `editor.md`, `domain-referee.md`, or `methods-referee.md` hard-codes a funder. What varies by
funder is this profile and the disposition weights.

**To adapt for a different funder:**

1. Add a new section below using `### Funder / Program Name (SHORT)`.
2. Fill each schema field:
   - **Focus** — what the funder supports (read the active call / solicitation and recent awards).
   - **Bar** — funding-rate context + one sentence on what the panel is looking for.
   - **Domain-referee adjustments** — re-weight Significance / Related Work / Substantive Argument / Scope & Transferability / Funder-Priority Alignment for this funder's taste.
   - **Methods-referee adjustments** — re-weight the grant-proposal dimensions (scientific rationale / feasibility / methodology soundness / timeline realism / team qualification / broader impact). If the funder uses a different rubric taxonomy, edit `methods-referee.md` accordingly.
   - **Typical concerns** — read the funder's published review criteria and any sample panel summaries; distill 3–5 recurring panelist questions.
   - **Panelist-pool weights** — the 6 dispositions (SIGNIFICANCE, INNOVATION, APPROACH-FEASIBILITY, TEAM-INVESTIGATORS, BROADER-IMPACT, SKEPTIC) are general enough for any funder. Re-weight based on what that funder's reviewers actually ask about. Weights must sum to 1.0.
   - **Desk-reject / decline criteria** — the funder's triage and eligibility rules.
   - **Table format** — page limits, required sections, any funder-specific conventions.

**Profile template (copy and fill):**

```markdown
### Funder / Program Name (SHORT)

**Short name:** `SHORT`
**Focus.** ...
**Bar.** ...
**Domain-referee adjustments.**
- Dimension X → Y (reason)
**Methods-referee adjustments.**
- Dimension X → Y (reason)
**Typical concerns.**
- "..."
**Panelist-pool weights.**
- SIGNIFICANCE: 0.xx
- INNOVATION: 0.xx
- APPROACH-FEASIBILITY: 0.xx
- TEAM-INVESTIGATORS: 0.xx
- BROADER-IMPACT: 0.xx
- SKEPTIC: 0.xx
**Desk-reject / decline criteria.** ...
**Table format override.** ...
```

---

## Cross-references

- `.claude/agents/editor.md` — reads this file (program officer).
- `.claude/agents/domain-referee.md` — applies domain-referee adjustments.
- `.claude/agents/methods-referee.md` — applies methods-referee adjustments.
- `.claude/skills/review-proposal/SKILL.md` — `--panel [funder]` mode entry point.
