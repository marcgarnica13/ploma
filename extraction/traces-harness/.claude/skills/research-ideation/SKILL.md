---
name: research-ideation
description: Generate structured research questions, testable hypotheses, and candidate empirical strategies from a topic, phenomenon, or dataset description. Use when user says "give me research ideas on X", "brainstorm questions about Y", "what could I study with this data?", "I'm looking for a paper idea on...", "generate hypotheses for...". One-shot generation, not multi-turn. For idea-refinement use `/interview-me`.
argument-hint: "[topic, phenomenon, or dataset description] [--no-verify]"
allowed-tools: ["Read", "Grep", "Glob", "Write", "WebSearch", "WebFetch", "Task"]
---

# Research Ideation

Generate structured research questions, testable hypotheses, and empirical strategies from a topic, phenomenon, or dataset.

**Input:** `$ARGUMENTS` — a topic (e.g., "process-mining offensive build-up play"), a phenomenon (e.g., "do teams have recurring zone-transition patterns?"), or a dataset description (e.g., "StatsBomb open events for one league season, via Mongo").

---

## Steps

1. **Understand the input.** Read `$ARGUMENTS` and any referenced files. Check `master_supporting_docs/` for related papers. Check `.claude/rules/` for domain conventions.

2. **Generate 3-5 research questions** ordered from descriptive to causal:
   - **Descriptive:** What are the patterns? (e.g., "What zone-transition flows recur in offensive possessions?")
   - **Correlational:** What is associated? (e.g., "Do higher-fitness possessions correlate with shots/goals?")
   - **Comparative:** How do groups differ? (e.g., "Do discovered nets differ across teams / leagues?")
   - **Mechanism:** Why does the pattern exist? (e.g., "Which design choice drives the discovered structure?")
   - **Application:** What is the takeaway? (e.g., "Can the model distinguish tactical styles usefully?")

3. **Tag each RQ with a likely paper type** (drawn from `methods-referee.md`):
   - `empirical-ML / computational-pipeline` (a method + pipeline demonstrated on data — the default here)
   - `methods / algorithm` (a new learning/mining algorithm)
   - `benchmark / empirical-study` (systematic comparison across datasets)
   - `application / case-study` (a domain application with an ML-general takeaway)
   - `unsure` (when multiple types are plausible — the user can pick later via `/interview-me`)

   Use `.claude/references/discipline-cards.md` to bias the distribution by field (the shipped `ml` card defaults to empirical-ML/computational-pipeline).

4. **For each research question, develop:**
   - **Hypothesis:** A testable prediction with an expected direction/magnitude
   - **Method / evaluation plan:** How to test it soundly (pipeline design, held-out / cross-validated evaluation, baselines, ablations)
   - **Data requirements:** What data would be needed? Is it available (Wyscout / StatsBomb via Mongo)?
   - **Key assumptions:** What must hold for the result to be valid / generalize?
   - **Potential pitfalls:** Common threats (data leakage, fit-on-train metrics, dataset-specific tuning, MongoDB-snapshot dependence)
   - **Related literature:** 2-3 papers using similar approaches (process mining + sports analytics)

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
**Paper type:** empirical-ML/computational-pipeline / methods / benchmark / application / unsure

**Hypothesis:** [Testable prediction]

**Method / Evaluation Plan:**
- **Method:** [e.g., heuristic-net discovery over possession traces]
- **Evaluation:** [held-out matches / cross-validation; metric]
- **Baseline:** [random / frequency / alternative discovery]
- **Key assumption:** [e.g., possessions are i.i.d. enough across matches to split]

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

1. **Negative-literature claims** — "no prior work applies process mining to X" is frequently wrong.
2. **Dataset structure claims** — "StatsBomb events contain field `obv_total_net`" can be confidently wrong about field names, coverage, or access status.
3. **Method feasibility claims** — "pm4py can compute alignment-based fitness on this log size" can misstate what the tool/method actually supports.

### Steps

1. **Extract claims** from the draft ideation report: each negative-literature claim, each named dataset with attributed fields, each claimed method + required data structure.
2. **Generate verification questions** per claim. Example: "Has anyone in the last 10 years applied process mining to soccer possession sequences? Search Google Scholar + arXiv." / "Do StatsBomb open events include the field you cite, in the seasons you need?"
3. **Spawn `claim-verifier`** via `Task` with `subagent_type=claim-verifier` and `context=fork`. Hand it claims + questions + source pointers (WebSearch allowed; arXiv / Semantic Scholar / OpenAlex preferred; dataset docs preferred). Do NOT include the draft.
4. **Reconcile:** PASS → attach green block; PARTIAL → mark uncertain RQs with flags; FAIL → rewrite the affected RQ/hypothesis/strategy.

### Skip conditions

- `--no-verify` flag
- User explicitly says "I'll verify the literature myself"

---

## Principles

- **Be creative but grounded.** Push beyond obvious questions, but every suggestion must be empirically feasible.
- **Think like a referee.** For each question, immediately identify the evaluation/validity challenge (how would you show it generalizes?).
- **Consider data availability.** A brilliant question with no available data is not actionable.
- **Suggest specific datasets** where possible (FRED, Census, PSID, administrative data, etc.).
