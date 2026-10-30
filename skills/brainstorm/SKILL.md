---
name: brainstorm
description: Turn a topic, phenomenon or dataset description into 3 to 5 structured research questions, from descriptive to application, each with a testable hypothesis, a method and evaluation plan, data requirements, key assumptions, pitfalls and related literature, tagged with a paper type from the project's discipline card and ranked by feasibility and contribution. When superpowers is enabled it runs superpowers:brainstorming first for the open-ended part. Literature, dataset and feasibility claims are fact-checked by a fresh-context verifier before the report is returned. Use when the user asks for research ideas, research questions, hypotheses, a paper idea, or what could be studied with some data. Not for refining one chosen idea (grill, spec) or for a literature search (lit-review).
argument-hint: "<topic, phenomenon or dataset description> [--no-verify]"
allowed-tools: Read, Glob, Grep, Write, Skill, Agent, WebSearch, WebFetch, Bash(python3 *)
---

Plugin root: if your shell lacks CLAUDE_PLUGIN_ROOT, prefix every command below with CLAUDE_PLUGIN_ROOT=<the directory two levels above this SKILL.md> (each shell call is a new process; an export does not carry over).

<!-- Ported from the traces harness research-ideation skill, which descends from pedrohcgs/claude-code-my-workflow (see UPSTREAMS.md). The source carries no attribution comment. -->

# ploma brainstorm

Arguments: `$ARGUMENTS`. Everything that is not a flag is the input: a topic, a phenomenon, or a description of a dataset. `--no-verify` skips the post-flight check. With no input, ask for one in a single sentence and stop.

No `ploma.yaml` in the repo root: say "ploma is not set up here. Run /ploma:onboard." and stop.

`<topic>` in file names is the input in lowercase, with every run of characters other than letters and digits replaced by one hyphen, trimmed to 60 characters.

## Context

1. Read the resolved config once:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/ploma_config.py" --json
   ```

2. Discipline card (`document.discipline`, `generic` when unset): Read `ploma.d/disciplines/<key>.yaml` if it exists, else `${CLAUDE_PLUGIN_ROOT}/disciplines/<key>.yaml`. Its `paper_types` (with `default_paper_type` first) are the paper types to tag with; its `sanity_checks`, `reproducibility_norms` and `challenge_examples` name the threats each question must face.
3. Read what the repo already holds, so no question repeats it: the manuscript (`document.main` and its inputs) when it exists, the files in each `literature.sources` directory (titles and abstracts; a PDF by page range with Read `pages`), earlier `<outputs.dir>/research_ideation_*.md` and `<outputs.dir>/lit_review_*.md` reports, and the bibliography: the files in `build.bib_files`, or, when that list is empty, the files the manuscript names in `\bibliography{...}` or `\addbibresource{...}` (the same discovery `bib_check.py` does).
4. If `<outputs.dir>/research_ideation_<topic>.md` exists, read it first. Build on it: add a dated section with the new questions instead of regenerating what is there.

## Open exploration (superpowers, when enabled)

superpowers is enabled when the session's skill list shows `superpowers:brainstorming`, or when this prints `"installed": true` (it reads the active host's plugin settings):

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/host.py" --json superpowers
```

- Enabled: after Context and before the research questions, invoke `superpowers:brainstorming` with the Skill tool, with the input and this goal: "explore research directions for a paper; the output is a set of research questions, not a software design". Use it only for the conversation and the play-back of what the user wants: the problem, the user's goals and constraints, and the directions worth pursuing.
  - Exit: stop before its "Size the Work" step. Write no design document, make no commit, spawn no builder-check subagent, and offer no visual companion or spike. Its HARD-GATE and its `superpowers:writing-plans` step do not apply: the ideation report below is the output.
  - At every fork, ploma's rule wins over superpowers' "ask them to describe first": offer options with the recommended one first and its reason.
  - Carry its outcome (the framing the user settled on, constraints, directions ruled in or out) into the research questions.
- Not enabled: say "superpowers is not enabled; running the ideation flow on its own (on Claude Code, install it with /plugin install superpowers@claude-plugins-official)." and go on.

## Research questions

Generate 3 to 5 research questions, ordered from descriptive to application:

- **Descriptive:** what are the patterns?
- **Correlational:** what is associated with what?
- **Comparative:** how do groups, settings or methods differ?
- **Mechanism:** why does the pattern exist; which design choice drives it?
- **Application:** what is the takeaway a reader can use?

Skip a rung the input cannot support rather than force one. For each question develop:

- **Hypothesis:** a testable prediction with an expected direction or size.
- **Method and evaluation:** how to test it soundly: the method, the evaluation regime the discipline card expects (held-out data, controls, baselines, ablations), the metric.
- **Data requirements:** what data it needs, whether the repo or a named public source has it, and how it is accessed. Name a dataset only when you can point to it.
- **Key assumptions:** what must hold for the result to be valid and to generalize.
- **Potential pitfalls:** the threats from the card's sanity checks that apply here (leakage, selection, in-sample evaluation, tuning to one dataset) and a mitigation for each.
- **Related literature:** two or three works using a similar approach, as author and year with a DOI or URL. Prefer works in the bibliography files or `literature.sources`; a work you cannot point to is written as a search direction ("work on X"), never as an invented citation.
- **Paper type:** one of the card's `paper_types` names, or `unsure` when several fit (the user picks later in /ploma:spec).

Think like a referee: every question carries its evaluation and validity challenge from the start. Be creative but grounded: a question with no reachable data is not actionable.

Then rank the questions by feasibility and contribution.

## Report

Write `<outputs.dir>/research_ideation_<topic>.md`:

```markdown
# Research Ideation: <topic as given>

**Date:** <YYYY-MM-DD>
**Input:** <the input verbatim>
**Discipline card:** <key>
**Exploration:** superpowers:brainstorming | ideation flow only

## Overview

<one or two paragraphs: the topic and why it matters; what the exploration settled>

## Research Questions

### RQ1: <question> (Feasibility: High | Medium | Low)

**Rung:** Descriptive | Correlational | Comparative | Mechanism | Application
**Paper type:** <card paper type name | unsure>
**Hypothesis:** <testable prediction>
**Method and evaluation:**
- **Method:** <method>
- **Evaluation:** <regime and metric>
- **Baseline:** <comparison>
**Data requirements:** <dataset, what it provides, access>
**Key assumptions:** <list>
**Potential pitfalls:** <threat and mitigation, one per line>
**Related literature:** <Author (Year), DOI or URL>

## Ranking

| RQ | Feasibility | Contribution | Priority |
|---|---|---|---|

## Suggested Next Steps

1. <the most promising direction and the immediate action>
2. <data to obtain>
3. <literature to read deeper: /ploma:lit-review "<query>">
```

## Post-flight verification

Unless `--no-verify` is given, run the protocol in `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/cove.md` on the draft report before returning it. Ideation is hallucination-prone in three ways; extract each as a claim:

1. Negative-literature claims ("no prior work applies X to Y").
2. Dataset claims (a named dataset, its fields, coverage or access).
3. Method feasibility claims (a named tool or method supports this data or scale).

Add every related-literature citation as a citation claim. Spawn `ploma:claim-verifier` (Agent tool, `subagent_type: ploma:claim-verifier`) with only the claims, the questions and the source pointers (bibliography files, `literature.sources` files, DOIs, URLs, search hints). Never the draft: the verifier never sees the report. Reconcile as `cove.md` says (outcome PASS, PARTIAL or FAIL from the tier counts; on FAIL rewrite the affected question from the verifier's evidence within the regeneration cap in limits). Append the `## Post-flight verification` block from `cove.md` to the report and to the reply. With `--no-verify`, the block says `**Outcome:** skipped (--no-verify)`.

## Record

The status is the post-flight outcome: PASS is PASS; PARTIAL, FAIL with the cap reached, verifier error and skipped are WARN.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/state.py" record brainstorm <PASS|WARN> --artifact <outputs.dir>/research_ideation_<topic>.md --extra questions=<count>
```

## Reply

The ranking table, one line per question (rung, paper type, hypothesis), the post-flight block and the report path. End with one line: "Pick a question and run /ploma:lit-review on it, or /ploma:grill to settle the open design decisions."
