# Prompt-Formatting Core (shared reference)

A general-purpose reference for shaping an informal request into a well-formed prompt. Defines the **structured-prompt skeleton** and the **depth-calibration heuristic**. Use it directly when you want to draft a careful prompt, and as the formatting contract that `/interview-me` (multi-turn spec building) can hand off to.

> Pattern adapted with attribution from Chris Blattman's [`claudeblattman` v2.1](https://github.com/chrisblattman/claudeblattman) (`skills/prompt-references/formatting-core.md`). Blattman-specific elements (tool-routing to ChatGPT / Perplexity / Gemini, the `council` token) are deliberately omitted — see this file's "What we don't ship" section.

---

## The structured-prompt skeleton

Every formatted prompt has six sections, in order. Some are optional at Light depth; all are present at Standard and Deep.

### 1. Role

One sentence naming the role Claude should adopt. Specific over generic.

- Generic (bad): "You are a helpful assistant."
- Specific (good): "You are a senior review-panel member for the target funder, calibrated to its significance and feasibility bar."

The role anchors the rest of the prompt; everything that follows is interpreted relative to it.

### 2. Task

One imperative sentence describing what to produce. Verb-first.

- Bad: "I'd like you to maybe think about whether we could possibly..."
- Good: "Identify the three weakest claims in this proposal's significance section."

### 3. Context

Brief grounding: what the user is working on, what's already known, what the agent should assume vs. ask about. Bulleted; ~5–8 items max at Standard depth.

For academic contexts, useful items:

- The paper's main contribution (one sentence).
- The methodological tradition (intervention trial / observational study / methods development / etc.).
- The target audience for the output (review panel / co-PI / program officer).
- Anything the user has already verified or ruled out.

### 4. Constraints

What the output MUST and MUST NOT do. Numbered if more than three. Bias toward MUST NOT — the absences are usually more informative than the presences.

- "MUST NOT recommend a different study design — the user has already committed to a randomized trial."
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

- Heuristic: input is 40–200 words OR contains 1+ domain-specific terms (funder-call / budget / eligibility jargon).
- What you emit: All six sections. Add an **Assumptions/Rationale** block at the end — "Here's what I inferred from the context; correct me if any of this is wrong." Two to four bullet points.
- Use case: "Help me think through whether our budget justification covers the indirect-cost cap."

### Deep

- Heuristic: input is > 200 words, OR mentions a specific paper / dataset / submission target, OR explicitly says "thorough", "detailed", "for submission".
- What you emit: All six sections + Assumptions block + an **Investigation pre-step** before the main task. The pre-step is one sentence describing what Claude should research / read / verify before producing the output. Example: "Pre-step: read the approach section of the proposal and the funder's current call guidelines before assessing whether the proposed timeline fits the funding period."
- Use case: "Draft a panel response to the three concerns in this resubmission."

### When to override

If the user types `depth:light` / `depth:standard` / `depth:deep`, honor it. The heuristic is a sensible default, not a contract.

---

## Worked example

**Input (conversational, dictated):**

> "ok so this panelist says our preliminary data is too thin to justify the headline aim, and that the budget over-asks on personnel. i think we can defend it by pointing to the pilot results and trimming one postdoc-month, but i want a clean response that takes the concern seriously. help me draft it."

**Depth inference:** Standard (input is ~55 words, mentions specific grant concepts "preliminary data / budget over-ask", and asks for a response document, not a quick reword).

**Formatted prompt (Standard, all six sections + Assumptions):**

```
Role
----
You are a PI drafting a response to a review panel's significance and
budget concern. The tone is firm but respectful — you neither concede
unnecessarily nor escalate.

Task
----
Draft a 1-paragraph response to the panel's claim that the preliminary
data is too thin to justify the headline aim, and that the personnel
budget over-asks.

Context
-------
- The current proposal cites pilot results to support the headline aim.
- The panel is right that the pilot is small; we can foreground its
  effect size and add the power calculation in the revision.
- We can trim one postdoc-month to reduce the personnel ask without
  cutting any aim.
- The resubmission policy is one revision; we cannot afford to escalate.

Constraints
-----------
1. MUST acknowledge the concern as legitimate before responding.
2. MUST commit to a concrete budget revision, not just argue.
3. MUST NOT overclaim what the pilot data shows.
4. SHOULD add the power calculation as a "we agree this is worth
   showing" gesture.

Output format
-------------
A single paragraph of 5-8 sentences in this structure:
1. Acknowledge the concern.
2. State what the pilot data does and does not show.
3. Commit to the budget revision.
4. Add the power calculation.
5. Optionally: note which sections/tables will be updated.

Bookend
-------
If anything above is ambiguous, ask one clarifying question before
drafting.

Assumptions
-----------
- The pilot supports a defensible effect-size estimate for a power
  calculation.
- The panelist is a feasibility skeptic, not objecting to the science
  per se.
- "Budget revision" means trimming personnel, unless an equipment line
  is the better cut.
- The contribution stays the proposed study; we are not switching aims
  in revision.
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

`/interview-me` is **multi-turn project specification** — a fuzzy research idea becomes a structured research spec (research question, hypotheses, method/evaluation plan, data needs) via Socratic Q&A. The output is a spec file used by `/research-ideation`, etc.

They don't compete. Use this skeleton when you want a well-formed ask. Use `/interview-me` when you want a well-formed research project. The former takes 30 seconds; the latter takes 10–20 minutes.
