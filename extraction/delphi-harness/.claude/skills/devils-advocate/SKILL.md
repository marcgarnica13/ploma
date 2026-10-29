---
name: devils-advocate
description: Adversarial 5-7 question challenge to the proposal's design choices — significance, feasibility, scope, methodology, budget/timeline realism, broader impact, funder fit. Use when user says "devil's advocate", "poke holes in this proposal", "push back on my approach", "stress-test the design", "what would a skeptical reviewer ask?". Read-only; surfaces questions to force rethinking.
argument-hint: "[proposal path] (defaults to proposal/)"
allowed-tools: ["Read", "Grep", "Glob"]
---

# Devil's Advocate Review

Critically examine the proposal (or a section/design choice) and challenge it with 5-7 specific questions.

**Philosophy:** "We arrive at the strongest possible proposal through active dialogue."

---

## Setup

1. **Read the target file(s)** (the proposal or section being challenged; default `proposal/` — `proposal/proposal_a4.tex` and, where relevant, `proposal/proposal_slides.tex`).
2. **Read the knowledge base** in `.claude/rules/` for conventions and project invariants.
3. If available, **read the funder profile** in `.claude/references/funder-profiles.md` to calibrate what the target funder rewards and penalizes.

---

## Challenge Categories

Generate 5-7 challenges from these categories:

### 1. Significance / Impact Challenges
> "Is the problem genuinely important, or incremental? Would the funder see this as worth their money?"

### 2. Feasibility Challenges
> "Can this team actually deliver the proposed work with the proposed resources in the proposed time? What is the riskiest deliverable and is there a fallback?"

### 3. Scope Challenges
> "Is the scope right-sized — not so broad it's unachievable, not so narrow it's trivial? Are the aims independent enough that one failing doesn't sink the rest?"

### 4. Methodology Challenges
> "Is the proposed approach the right one, and is it justified over alternatives? Are success criteria and evaluation concrete and measurable?"

### 5. Budget / Timeline Realism Challenges
> "Does the budget match the work plan? Are personnel, equipment, and timeline credible, or is something under- or over-resourced? Do milestones line up with deliverables?"

### 6. Broader Impact Challenges
> "Is the broader impact (scientific, societal, training, dissemination) substantive or boilerplate? Who benefits, and how is that demonstrated?"

### 7. Funder-Fit Challenges
> "Does this match the funder's mission, scheme, and review criteria? Is the framing aligned with what this specific call rewards?"

---

## Output Format

```markdown
# Devil's Advocate: [Proposal Title]

## Challenges

### Challenge 1: [Category] — [Short title]
**Question:** [The specific question]
**Why it matters:** [What could go wrong]
**Suggested resolution:** [Specific action]
**Sections affected:** [Numbers or titles]
**Severity:** [High / Medium / Low]

[Repeat for 5-7 challenges]

## Summary Verdict
**Strengths:** [2-3 things done well]
**Critical changes:** [0-2 changes before submission]
**Suggested improvements:** [2-3 nice-to-have changes]
```

---

## Principles

- **Be specific:** Reference exact sections, aims, work packages, and budget lines.
- **Be constructive:** Every challenge has a suggested resolution.
- **Be honest:** If the proposal is strong, say so.
- **Prioritize:** Significance / feasibility > minor framing.
- **Think like a skeptical reviewer:** Where would they push back hardest?
