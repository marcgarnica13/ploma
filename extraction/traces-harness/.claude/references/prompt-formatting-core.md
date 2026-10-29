# Prompt-Formatting Core (shared reference)

A general-purpose reference for shaping an informal request into a well-formed prompt. Defines the **structured-prompt skeleton** and the **depth-calibration heuristic**. Use it directly when you want to draft a careful prompt, and as the formatting contract that `/interview-me` (multi-turn spec building) can hand off to.

> Pattern adapted with attribution from Chris Blattman's [`claudeblattman` v2.1](https://github.com/chrisblattman/claudeblattman) (`skills/prompt-references/formatting-core.md`). Blattman-specific elements (tool-routing to ChatGPT / Perplexity / Gemini, the `council` token) are deliberately omitted — see this file's "What we don't ship" section.

---

## The structured-prompt skeleton

Every formatted prompt has six sections, in order. Some are optional at Light depth; all are present at Standard and Deep.

### 1. Role

One sentence naming the role Claude should adopt. Specific over generic.

- Generic (bad): "You are a helpful assistant."
- Specific (good): "You are a senior referee for the Springer *Machine Learning* journal, calibrated to its evaluation-validity and reproducibility bar."

The role anchors the rest of the prompt; everything that follows is interpreted relative to it.

### 2. Task

One imperative sentence describing what to produce. Verb-first.

- Bad: "I'd like you to maybe think about whether we could possibly..."
- Good: "Identify the three weakest steps in this paper's identification strategy."

### 3. Context

Brief grounding: what the user is working on, what's already known, what the agent should assume vs. ask about. Bulleted; ~5–8 items max at Standard depth.

For academic contexts, useful items:

- The paper's main contribution (one sentence).
- The methodological tradition (reduced-form / structural / formal-theory / etc.).
- The target audience for the output (referee / co-author / student).
- Anything the user has already verified or ruled out.

### 4. Constraints

What the output MUST and MUST NOT do. Numbered if more than three. Bias toward MUST NOT — the absences are usually more informative than the presences.

- "MUST NOT recommend a different discovery algorithm — the user has already committed to the heuristics miner."
- "MUST return findings as a numbered list with severity tags (CRITICAL / IMPORTANT / MINOR)."

### 5. Output format

Concrete shape of the output. The more specific, the better.

- Bad: "Give me a thorough analysis."
- Good: "Return a Markdown table with columns: Finding, Severity, Why-it-matters, Suggested-fix. One row per finding, max 10 rows."

### 6. Bookend

The closing instruction. Almost always: "If anything in the above is ambiguous, ask one clarifying question before proceeding."

The bookend is what catches the cases where the prompt was almost-but-not-quite specific enough. Without it, Claude guesses; with it, you get one focused question that improves the rest of the run.

---

## Depth calibration

A `depth:` setting (`light` / `standard` / `deep`) controls how much of the skeleton you emit. The depth heuristic picks a default when the user doesn't specify.

### Light (default)

- Heuristic: input is conversational (< 40 words) and contains no domain-specific terminology, OR explicitly says "quick", "just", "small".
- What you emit: Role + Task + Output Format (+ Bookend). Skip Context and Constraints.
- Use case: "Reword this paragraph for clarity." / "What's a good R package for X?"

### Standard

- Heuristic: input is 40–200 words OR contains 1+ domain-specific terms (process mining / ML / evaluation jargon).
- What you emit: All six sections. Add an **Assumptions/Rationale** block at the end — "Here's what I inferred from the context; correct me if any of this is wrong." Two to four bullet points.
- Use case: "Help me think through whether the fitness evaluation is leaking test data."

### Deep

- Heuristic: input is > 200 words, OR mentions a specific paper / dataset / submission target, OR explicitly says "thorough", "detailed", "for submission".
- What you emit: All six sections + Assumptions block + an **Investigation pre-step** before the main task. The pre-step is one sentence describing what Claude should research / read / verify before producing the output. Example: "Pre-step: read the methods section of the manuscript and the `discovery.py` module before assessing whether the reported fitness is measured out-of-sample."
- Use case: "Draft a referee response to the three concerns in this R&R."

### When to override

If the user types `depth:light` / `depth:standard` / `depth:deep`, honor it. The heuristic is a sensible default, not a contract.

---

## Worked example

**Input (conversational, dictated):**

> "ok so this referee says our fitness number doesn't mean anything because we report it on the same matches we discovered the net from. i think we can defend it by adding a held-out evaluation and a baseline, but i want a clean response that takes the concern seriously. help me draft it."

**Depth inference:** Standard (input is ~50 words, mentions a specific ML concept "evaluate on the same data you fit on", and asks for a response document, not a quick reword).

**Formatted prompt (Standard, all six sections + Assumptions):**

```
Role
----
You are an applied ML researcher drafting a response to a referee's
evaluation-validity concern. The tone is firm but respectful — you
neither concede unnecessarily nor escalate.

Task
----
Draft a 1-paragraph response to the referee's claim that reporting
conformance fitness on the discovery data does not demonstrate
generalization.

Context
-------
- The current paper reports token-replay fitness on the same matches
  the heuristic net was discovered from.
- The referee is right that this is not evidence of generalization.
- We can add a held-out evaluation (discover on a train split of
  matches, evaluate fitness on held-out matches) and a baseline
  (random / frequency model) within the revision.
- The R&R policy is one revision; we cannot afford to escalate.

Constraints
-----------
1. MUST acknowledge the concern as legitimate before responding.
2. MUST commit to a held-out evaluation, not just argue.
3. MUST NOT overclaim what fitness measures.
4. SHOULD add a baseline comparison as a "we agree this is worth
   showing" gesture.

Output format
-------------
A single paragraph of 5-8 sentences in this structure:
1. Acknowledge the concern.
2. State what fitness does and does not measure.
3. Commit to the held-out evaluation protocol.
4. Add the baseline comparison.
5. Optionally: note which tables/figures will be updated.

Bookend
-------
If anything above is ambiguous, ask one clarifying question before
drafting.

Assumptions
-----------
- The data supports a train/test split by match without too few
  possessions per split.
- The referee is an evaluation skeptic, not objecting to process
  mining per se.
- "Baseline" means a random / frequency model, unless a published
  alternative is expected.
- The contribution stays the process-mining pipeline; we are not
  switching methods in revision.
```

Notice the assumptions block. If any of those four assumptions are wrong, the user corrects them in one message and we re-emit — much cheaper than running the unformatted prompt and discovering the misalignment downstream.

---

## What we don't ship (intentionally)

Blattman's original prompt skill includes:

- A **tool-routing table** that suggests dispatching to ChatGPT / Perplexity Deep Research / Gemini when those tools serve the task better. This bakes in a multi-vendor workflow not every forker maintains. If you want tool routing, add your own table to this file.
- A **`council` token** that dispatches the formatted prompt to a five-critic multi-model deliberation. This repo doesn't ship that — we have `/seven-pass-review`, `/devils-advocate`, and the `promote-memory-council` agent instead, which serve adjacent purposes with different shapes.

If you add your own multi-vendor or multi-model fan-out, extend this file with your routing rules. Keep them in this reference so callers stay aligned.

---

## Boundary with `/interview-me`

Single-shot prompt shaping (this reference) turns one informal request into one well-formed prompt. There is no multi-turn elaboration.

`/interview-me` is **multi-turn project specification** — a fuzzy research idea becomes a structured research spec (research question, hypotheses, method/evaluation plan, data needs) via Socratic Q&A. The output is a spec file used by `/research-ideation`, `/data-analysis`, etc.

They don't compete. Use this skeleton when you want a well-formed ask. Use `/interview-me` when you want a well-formed research project. The former takes 30 seconds; the latter takes 10–20 minutes.
