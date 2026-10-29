# Prompt formatting

How to turn an informal request into a well-formed prompt, for a subagent or for the user to reuse. Pattern adapted with attribution from Chris Blattman's `claudeblattman` prompt references.

## The six-part skeleton

1. **Role.** One specific sentence. "You are a referee for <venue.profile>, calibrated to its reproducibility bar" beats "You are a helpful assistant".
2. **Task.** One imperative sentence, verb first. "Identify the three weakest steps in the evaluation."
3. **Context.** Five to eight bullets: the main contribution in one sentence, the method tradition, the audience for the output, what is already verified or ruled out. Take facts from `ploma.yaml` and the spec, never from memory.
4. **Constraints.** What the output MUST and MUST NOT do, numbered when more than three. Prefer MUST NOT; absences carry more information.
5. **Output format.** The concrete shape: "a Markdown table with columns Finding, Severity, Why it matters, Fix; at most ten rows".
6. **Bookend.** "If anything above is ambiguous, ask one clarifying question before proceeding."

## Depth

| Depth | When | Emit |
|---|---|---|
| light | under 40 words, no field jargon, or "quick" | role, task, format, bookend |
| standard | 40 to 200 words, or field terms | all six parts plus an Assumptions block of two to four bullets |
| deep | over 200 words, a specific paper or submission | all six, Assumptions, and an investigation pre-step naming what to read first |

An explicit `depth:light|standard|deep` overrides the heuristic.

The Assumptions block lists what you inferred. A wrong assumption costs one correction message instead of a wasted run.

## Boundary

This is single-shot prompt shaping. Multi-turn project specification is `/ploma:grill` followed by `/ploma:spec`.
