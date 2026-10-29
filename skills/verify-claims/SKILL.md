---
name: verify-claims
description: Fact-check the factual claims in the manuscript or another draft with Chain-of-Verification. Extracts citation, named-entity, negative-literature and dataset claims, writes one verification question each, and hands only the claims, the questions and the source pointers to a fresh-context claim-verifier agent that never sees the draft. Reports a verdict and a tier per claim and records the claims entry of the commit gate. Use when the user asks to verify citations, fact-check the paper or a draft, check what the paper says about cited work, or asks whether anything was hallucinated. Not for grammar (proofread) or for the paper's own result numbers (audit-reproducibility).
argument-hint: "[file] [--source <path-or-url>]..."
allowed-tools: Read, Glob, Grep, Write, Agent, Bash(python3 *)
---

# ploma verify-claims

Arguments: `$ARGUMENTS`. A file path checks that file (a `.tex`, `.md` or text draft). Without one, check the manuscript: `document.main` and every `.tex` file under `document.root`, leaving out `*_suggestion.tex`. Each `--source <path-or-url>` adds a source pointer; repeat it for several.

No `ploma.yaml` in the repo root: say "ploma is not set up here. Run /ploma:onboard." and stop.

This skill follows `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/cove.md`. Read it first. It checks the draft and never rewrites it: the regeneration step of that page does not apply here. Each discrepancy becomes a finding with a proposed fix, and the user decides.

## Phase 0: Pre-flight

1. Read the resolved config once:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/ploma_config.py" --json
   ```

2. The file or files to check exist and are readable. `<stem>` is the checked file's name without its extension (the main file's for a manuscript run). A manuscript run checks `document.main` with all its inputs (no file argument, or the main file named); any other file, a single section included, is a partial run.
3. Source pointers: every `--source`, plus the bibliography files in `build.bib_files`, plus any local copies of cited works the user names. With no pointer at all, say so and stop.

## Phase 1: Extract claims

Read the draft. List every factual assertion of these kinds, with its location (`file:line`) and the verbatim sentence:

| Kind | Shape |
|---|---|
| Citation | "Author (Year) shows X", or a sentence ending in `\cite{key}` that says what the cited work did |
| Named entity | a person, paper title, venue, software and version, algorithm or method name |
| Negative literature | "no prior work does X", "the first to" |
| Dataset or resource | "dataset D contains field F", "library L provides function f" |
| Number from a cited work | a value the draft attributes to another paper |

Skip opinions, plans, definitions the draft introduces, and the paper's own result numbers (those are checked by `scripts/consistency.py` and `/ploma:audit-reproducibility`). With no claims left, say "no verifiable factual claims found; nothing to check" and stop without a gate entry.

Show the claims table:

```markdown
| ID | Claim | Location | Source hint |
|---|---|---|---|
| C1 | <one sentence> | <file:line> | <bib key, file or URL> |
```

## Phase 2: Verification questions

One specific question per claim, answerable from its source alone, with the source pointer attached (bib key and file, local path, DOI or URL), as `cove.md` describes.

## Phase 3: Fresh-context verification

Spawn `ploma:claim-verifier` (Agent tool, `subagent_type: ploma:claim-verifier`) with a prompt that holds only the YAML block from `cove.md`: `source_material`, `doi_lookup_cap` and `claims` with `id`, `text`, `source_hint` and `verification_question`. Never pass the draft, a summary of it, the surrounding section or this conversation. For a long claim list, split it into batches and spawn one verifier per batch in the same message; each batch carries only its own claims and sources.

The verifier runs the citation lookups itself within the DOI lookup cap (`limits.doi_lookups_per_run`). Parallel batches share that cap: each batch block carries `doi_lookup_cap: <floor(cap / batches)>` (at least 1), which the verifier passes to the lookup script as `--max <floor(cap / batches)>`. A single verifier gets the whole cap.

## Phase 4: Reconcile

Map each verifier match to a report verdict:

| Verifier match | Report verdict |
|---|---|
| `yes` | SUPPORTED |
| `partial` | PARTIAL (with its tier, if any) |
| `no` | CONTRADICTED (always HIGH-WARN) |
| `cannot-verify` | UNVERIFIABLE (with its tier: HIGH for a fabricated reference, MED for a transient failure, LOW for an inaccessible source) |
| `not-verifiable-claim-type` | excluded: listed under "Not verifiable (claim type)", not counted |

Outcome, from the tier counts only (the rule in `cove.md`):

- **PASS**: 0 HIGH-WARN and 0 MED-WARN, whatever the LOW-WARN count. LOW-WARN claims are listed under "LOW-WARN (advisory, non-gating)".
- **PARTIAL**: 0 HIGH-WARN and at least one MED-WARN.
- **FAIL**: at least one HIGH-WARN (a contradiction or a fabricated reference).

`not-verifiable-claim-type` claims are excluded from the counts and listed separately. A MED-WARN or LOW-WARN never counts as a contradiction: an unreachable source concluded nothing.

Fail closed: if a verifier errors, times out or returns no per-claim table, the claims it held are not checked. Say "Claim verification failed (<reason>). The draft has not been independently checked." Record the state event as FAIL and do not record a gate entry: a missing verification is never a PASS.

## Phase 5: Report

Write `<outputs.dir>/verify_claims_<stem>.md`. It opens with the header in `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/report-header.md` (title "Claim Verification (CoVe)"), then a method line: "Fresh-context ploma:claim-verifier; it received the claims, the questions and the source pointers, never the draft." Then:

```markdown
## Result: <PASS | PARTIAL | FAIL>: <V> of <N> claims verified, <H> HIGH-WARN

| ID | Claim | Location | Verdict | Tier | Evidence |
|---|---|---|---|---|---|
| C1 | <claim> | <file:line> | SUPPORTED / PARTIAL / CONTRADICTED / UNVERIFIABLE | none / LOW / MED / HIGH | <source and location, DOI or URL> |

## HIGH-WARN (gate FAIL)

## MED-WARN (retry recommended)

## LOW-WARN (advisory, non-gating)

## Not verifiable (claim type)
```

Each HIGH-WARN, MED-WARN and LOW-WARN entry is a finding in the format of `${CLAUDE_PLUGIN_ROOT}/skills/_shared/references/finding-format.md`: location (`file:line` and claim id), the current sentence verbatim, the fix (what the source supports, a corrected citation, or the source the user should supply), and the severity (HIGH-WARN is CRITICAL, MED-WARN is MAJOR, LOW-WARN is MINOR). An empty section says "None." If the report exists, read it and add a dated section instead of overwriting.

## Record

The gate entry is FAIL on any HIGH-WARN and PASS otherwise (PARTIAL records PASS: MED and LOW never gate). The state event carries the outcome (PASS is PASS, PARTIAL is WARN, FAIL is FAIL):

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/gate.py" record claims <PASS|FAIL> --artifact <outputs.dir>/verify_claims_<stem>.md --extra high=<H>
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/state.py" record verify-claims <PASS|WARN|FAIL> --artifact <outputs.dir>/verify_claims_<stem>.md
```

Record the gate entry only for a manuscript run (the main file with all its inputs). A partial run (one section file, or a draft outside the manuscript) records the state event only and says so in the reply: "Partial run: claims gate entry not recorded." There is no flag that softens a HIGH-WARN. When the author judges a HIGH-WARN wrong, the commit gate override covers it: `commit anyway: <reason>` at `/ploma:commit`, which logs the reason.

## Reply

Quote the Result line and the claims table. Then each HIGH-WARN with its evidence and fix, the MED and LOW counts with one line each, and the gate entry recorded. End with one line, the first that applies:

- FAIL: "Fix the HIGH-WARN claims above, then run /ploma:verify-claims again."
- PARTIAL: "Supply the sources for the unverified claims, or re-run /ploma:verify-claims later for the MED-WARN ones."
- PASS: "Claims verified. Run /ploma:proofread next if it has not run on these files."
