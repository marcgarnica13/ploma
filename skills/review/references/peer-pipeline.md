<!-- Adapted from Hugo Sant'Anna's clo-author (github.com/hugosantanna/clo-author),
     used with permission. Editor persona, disposition taxonomy, and pipeline shape
     credit: Hugo Sant'Anna. -->

# Peer-review pipeline (`--peer <venue>`)

A simulated editorial process: editor desk review, referee selection, two blind referees with deliberately different dispositions, editorial synthesis. It differs from `--adversarial` in kind: different personas whose priors disagree and who never see each other's reports.

The editor spawns no agents itself (an agent cannot spawn agents). This skill orchestrates every step: it spawns each agent with the Agent tool, writes the files the agents return (they have no write tool), and passes paths, never the other agents' reports, between steps.

All files of one review live in `<outputs.dir>/peer_review_<slug>/` (create it with `mkdir -p`).

| File | Step | Rounds |
|---|---|---|
| `desk_review.md` | editor desk review and referee selection | fresh run only |
| `referee_domain.md`, `referee_methods.md` | the two referees | `_r<N>` suffix in round N: `referee_domain_r<N>.md` |
| `editorial_decision.md` | editor synthesis | `editorial_decision_r<N>.md` |
| `stress_gauntlet.md` | editor synthesis in `--stress` | fresh run only |
| `referee_1.md` to `referee_<N>.md`, `decision_distribution.md`, `editor_synthesis.md` | `--variance N` | fresh run only |

A file that already exists from an earlier run of the same kind is read first and replaced only after the user agrees (`AskUserQuestion`: "Replace the earlier review" or "Stop"); without the tool, stop and name the file.

## Phase 0: before any agent

Run in this order and stop at the first failure:

1. The flag checks of the skill (mutually exclusive flags, round and variance caps).
2. Venue resolution with `profiles.py` (in the skill). An unknown key stops here.
3. Revise-and-resubmit round `--r<N>`: the prior round's files exist (`referee_domain.md` and `referee_methods.md` for N = 2, `referee_domain_r<N-1>.md` and `referee_methods_r<N-1>.md` after that, and `desk_review.md`). Missing: stop and say which file and which earlier command produces it.
4. Cross-artifact, when it applies (see the skill): `/ploma:audit-reproducibility --no-rerun` runs now, before the desk review. Its result goes into the Pre-Flight Report.
5. Print the Pre-Flight Report before spawning any agent, in the format of `report-templates.md`. It names the manuscript, the resolved venue, the discipline, the round, the novelty-check state and the cross-artifact status. The user sees exactly what the pipeline will use.

## Phase 1: Desk review (fresh runs only)

Spawn `ploma:editor` (Agent tool, `subagent_type: ploma:editor`). The prompt holds: the manuscript path and its input files, the venue key, `outputs.dir` and `<slug>`, the phases to run (desk review, then referee selection when it sends out), the mode (default, `stress` or `variance N`), whether the novelty check is off (`--no-novelty-check`), and the reproducibility audit report path when the audit ran. Write the returned `desk_review.md`.

### Novelty post-flight

The novelty probes use web search, which can return fabricated or misattributed prior work. Before any novelty claim counts, verify it per `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/cove.md`:

1. Take the rows of the `## Novelty claims` table in `desk_review.md`. None, or `--no-novelty-check`: skip this step.
2. Spawn `ploma:claim-verifier` with only the YAML block of `cove.md`: `source_material` (the URLs and DOIs from the table) and `claims` (id, the claim, a source hint, one verification question each). Never pass the manuscript, the desk review or a summary of either.
3. Append `## Novelty post-flight` to `desk_review.md`: verified claims stay as evidence; every other claim moves under "editor could not verify, manual check recommended", with the verifier's reason. A verifier error is fail closed: every claim is unverified.
4. If the verdict is DESK REJECT for "already done" and the deciding claim is not verified, spawn `ploma:editor` once more. Its prompt holds the same inputs as the first spawn (the manuscript path and inputs, the venue key, `outputs.dir` and `<slug>`, the mode, the novelty-check state, the audit report path when the audit ran) plus the desk review path and the post-flight table, asking for a new verdict without that claim. If the new verdict is SEND OUT, the returned desk review must include the `## Referee Selection` table; without it, stop and say the referee selection is missing. Write its returned desk review over the first.

DESK REJECT: stop here. Show the reason, the evidence and the suggested venue, and record the run (`decision=desk-reject`).

## Phase 2: Referees, blind to each other

Read the `## Referee Selection` table in `desk_review.md` (round N: the same table, from the fresh run). Spawn `ploma:domain-referee` and `ploma:methods-referee` both in one message, so they run in parallel and neither waits on or sees the other. Each prompt holds only:

- the manuscript path and its input files;
- the path of `desk_review.md` and this referee's row: its disposition, critical peeve(s) and constructive peeve;
- `outputs.dir`, `<slug>` and the target file name (`referee_domain.md`, or `referee_domain_r<N>.md`; likewise for methods);
- round N only: the path of this referee's prior report and the instruction to classify each prior major concern RESOLVED, PARTIAL or NOT ADDRESSED;
- `--stress` only: "You are looking for reasons to reject this paper. Be hostile but fair."
- "Read only the files named in this prompt." (plus the venue and discipline files of your Project context)

Never pass one referee's report, or a summary of it, to the other. Write each returned report to its file.

### Variance (`--variance N`)

The editor's selection table has N rows. Spawn N referees all in one message: odd rows `ploma:domain-referee`, even rows `ploma:methods-referee`, each with its own row and the target `referee_<i>.md`. Same isolation rules.

## Phase 3: Editor synthesis

Spawn a fresh `ploma:editor` with: the venue key, the manuscript path and inputs (for the quote check), the paths of `desk_review.md` and of every referee report of this round, the mode and the round. The editor runs its quote check and returns:

- default: `editorial_decision.md` (round N: `editorial_decision_r<N>.md`);
- `--stress`: the concern gauntlet, written to `stress_gauntlet.md`;
- `--variance N`: `decision_distribution.md` and `editor_synthesis.md`.

Write the returned files. Check that the decision letter has its `## Dropped findings (quote not found)` section; if it is missing, say the quote check did not run and treat the decision as provisional.

## Fail closed

An agent that errors, times out or returns no file content stops the pipeline at that phase. Say which phase failed and which files exist, and record the run as FAIL. Never write a referee report or a decision yourself in place of an agent's.

## Phase 4: Summary

Tell the user: the decision (Accept, Minor revision, Major revision, Reject, Desk reject; for variance the modal verdict and spread; for stress the count of concerns), each referee's disposition and score, the FATAL and ADDRESSABLE concerns with locations, the dropped-finding count, the novelty post-flight outcome, and the path of every file written.

Novelty caveat, always stated when the probes ran: web search can miss paywalled or recent work and can invent citations; novelty results are flags for manual checking, not verdicts.
