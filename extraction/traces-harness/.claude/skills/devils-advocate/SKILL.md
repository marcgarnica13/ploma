---
name: devils-advocate
description: Adversarial 5-7 question challenge to the paper's design choices — framing, method choices, evaluation, scope, ordering of the argument. Use when user says "devil's advocate", "poke holes in this paper", "push back on my method", "stress-test the design", "what would a skeptical referee ask?". Read-only; surfaces questions to force rethinking.
argument-hint: "[manuscript path] (defaults to manuscript/samplepaper.tex)"
allowed-tools: ["Read", "Grep", "Glob"]
---

# Devil's Advocate Review

Critically examine the manuscript (or a method/design proposal) and challenge it with 5-7 specific questions.

**Philosophy:** "We arrive at the best possible paper through active dialogue."

---

## Setup

1. **Read the target file** (the manuscript or section being challenged; default `manuscript/samplepaper.tex`).
2. **Read the knowledge base** in `.claude/rules/` for notation conventions and project invariants.
3. If applicable, **read the prior-round reviews** in `review/review1–3.md` for context on what referees already objected to.

---

## Challenge Categories

Generate 5-7 challenges from these categories:

### 1. Framing / Contribution Challenges
> "Is the ML-general contribution crisp, or is this just a soccer application of an off-the-shelf method?"

### 2. Method-Choice Challenges
> "Why this abstraction (24 zones, `action##zone` key, heuristic-net discovery) and not a coarser/finer or alternative one? Is the choice justified or convenient?"

### 3. Evaluation / Validity Challenges
> "Is fitness reported on held-out data? Where is the baseline? What would falsify the claim?"

### 4. Generalization Challenges
> "Would this hold on another season / competition / data provider (Wyscout vs StatsBomb)? Or is it tuned to this dataset?"

### 5. Scope / Claim Challenges
> "Does the conclusion overreach what the method can actually distinguish (tactical claims vs what the model encodes)?"

### 6. Argument-Ordering Challenges
> "Could a reader follow this better if the contribution / evaluation regime were stated earlier?"

### 7. Related-Work Challenges
> "Is the prior work fairly covered across BOTH process mining and sports analytics, and is the delta over the previous conference version clear?"

---

## Output Format

```markdown
# Devil's Advocate: [Paper Title]

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

- **Be specific:** Reference exact sections, equations, and configurations.
- **Be constructive:** Every challenge has a suggested resolution.
- **Be honest:** If the paper is strong, say so.
- **Prioritize:** Validity / generalization > minor framing.
- **Think like a skeptical referee:** Where would they push back hardest?
