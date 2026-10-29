---
name: research-ideation
description: Generate structured research questions, testable hypotheses, and candidate empirical strategies from a topic, phenomenon, or dataset description. Use when user says "give me research ideas on X", "brainstorm questions about Y", "what could I study with this data?", "I'm looking for a paper idea on...", "generate hypotheses for...". One-shot generation, not multi-turn. For idea-refinement use `/interview-me`.
argument-hint: "[topic, phenomenon, or dataset description] [--no-verify]"
allowed-tools: ["Read", "Grep", "Glob", "Write", "WebSearch", "WebFetch", "Task"]
---

# Research Ideation

Generate structured research questions, testable hypotheses, and empirical strategies from a topic, phenomenon, or dataset.

**Input:** `$ARGUMENTS` — a topic (e.g., "a telehealth intervention for post-discharge recovery"), a phenomenon (e.g., "do remote-monitored patients have fewer readmissions?"), or a dataset description (e.g., "240 enrolled participants across three clinical sites over two years").

---

## Steps

1. **Understand the input.** Read `$ARGUMENTS` and any referenced files. Check `master_supporting_docs/` for related papers. Check `.claude/rules/` for domain conventions.

2. **Generate 3-5 research questions** ordered from descriptive to causal:
   - **Descriptive:** What are the patterns? (e.g., "What is the baseline rate of post-discharge readmission?")
   - **Correlational:** What is associated? (e.g., "Is adherence associated with better recovery outcomes?")
   - **Comparative:** How do groups differ? (e.g., "Do outcomes differ across enrollment sites or subgroups?")
   - **Mechanism:** Why does the effect exist? (e.g., "Which component of the intervention drives the effect?")
   - **Application:** What is the takeaway? (e.g., "Can the intervention be scaled to routine care?")

3. **Tag each RQ with a likely study type** (drawn from `methods-referee.md`):
   - `clinical-trial / interventional` (a prospective test of an intervention — the default here)
   - `observational / cohort` (association in non-randomized data)
   - `pilot / feasibility` (small-N test of recruitment, adherence, and procedures)
   - `secondary-analysis / case-study` (reuse of existing data with a generalizable takeaway)
   - `unsure` (when multiple types are plausible — the user can pick later via `/interview-me`)

   Use the type definitions in `methods-referee.md` to frame the proposed study.

4. **For each research question, develop:**
   - **Hypothesis:** A testable prediction with an expected direction/magnitude
   - **Method / evaluation plan:** How to test it soundly (study design, randomization, primary endpoint, powered sample, sensitivity analyses)
   - **Data requirements:** What data would be needed? Is it available (enrollment, EHR linkage, follow-up windows)?
   - **Key assumptions:** What must hold for the result to be valid / generalize?
   - **Potential pitfalls:** Common threats (selection bias, attrition, underpowering, single-site dependence)
   - **Related literature:** 2-3 papers/trials using similar approaches in the proposal's field

5. **Rank the questions** by feasibility and contribution.

6. **Save the output** to `quality_reports/research_ideation_[sanitized_topic].md`

---

## Output Format

```markdown
# Research Ideation: [Topic]

**Date:** [YYYY-MM-DD]
**Input:** [Original input]

## Overview

[1-2 paragraphs situating the topic and why it matters]

## Research Questions

### RQ1: [Question] (Feasibility: High/Medium/Low)

**Type:** Descriptive / Correlational / Causal / Mechanism / Application
**Study type:** clinical-trial/interventional / observational / pilot / secondary-analysis / unsure

**Hypothesis:** [Testable prediction]

**Method / Evaluation Plan:**
- **Method:** [e.g., two-arm randomized controlled trial]
- **Evaluation:** [primary endpoint at follow-up; pre-specified analysis]
- **Comparator:** [usual care / active control / waitlist]
- **Key assumption:** [e.g., randomization balances confounders across arms]

**Data Requirements:**
- [Dataset 1 — what it provides]
- [Dataset 2 — what it provides]

**Potential Pitfalls:**
1. [Threat 1 and possible mitigation]
2. [Threat 2 and possible mitigation]

**Related Work:** [Author (Year)], [Author (Year)]

---

[Repeat for RQ2-RQ5]

## Ranking

| RQ | Feasibility | Contribution | Priority |
|----|-------------|-------------|----------|
| 1  | High        | Medium      | ...      |
| 2  | Medium      | High        | ...      |

## Suggested Next Steps

1. [Most promising direction and immediate action]
2. [Data to obtain]
3. [Literature to review deeper]
```

---

## Post-Flight Verification (mandatory, CoVe)

Before returning the ideation report, run the Post-Flight Verification protocol from [`.claude/rules/post-flight-verification.md`](../../rules/post-flight-verification.md). Research ideation is hallucination-prone in three specific ways:

1. **Negative-literature claims** — "no prior trial has tested intervention X" is frequently wrong.
2. **Dataset/cohort claims** — "the registry captures field `readmit_30d`" can be confidently wrong about field names, coverage, or access status.
3. **Method feasibility claims** — "240 participants gives 80% power to detect this effect" can misstate what the design actually supports.

### Steps

1. **Extract claims** from the draft ideation report: each negative-literature claim, each named dataset/cohort with attributed fields, each claimed method + required data structure.
2. **Generate verification questions** per claim. Example: "Has any trial in the last 10 years tested this intervention for this population? Search PubMed + ClinicalTrials.gov." / "Does the registry you cite include that field, for the years you need?"
3. **Spawn `claim-verifier`** via `Task` with `subagent_type=claim-verifier` and `context=fork`. Hand it claims + questions + source pointers (WebSearch allowed; arXiv / Semantic Scholar / OpenAlex preferred; dataset docs preferred). Do NOT include the draft.
4. **Reconcile:** PASS → attach green block; PARTIAL → mark uncertain RQs with flags; FAIL → rewrite the affected RQ/hypothesis/strategy.

### Skip conditions

- `--no-verify` flag
- User explicitly says "I'll verify the literature myself"

---

## Principles

- **Be creative but grounded.** Push beyond obvious questions, but every suggestion must be empirically feasible.
- **Think like a reviewer.** For each question, immediately identify the evaluation/validity challenge (how would you show it generalizes?).
- **Consider data availability.** A brilliant question with no available data is not actionable.
- **Suggest specific data sources** where possible (registries, EHR/claims, administrative data, existing cohorts, etc.).
