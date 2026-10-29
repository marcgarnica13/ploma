<!-- Adapted from Dhuliawala et al. 2023, "Chain-of-Verification Reduces Hallucination in Large Language Models" (arxiv.org/abs/2309.11495). -->

# Chain-of-Verification (post-flight)

Skills whose output holds checkable facts (citations, numbers, named entities, negative literature claims, "we added X on page Y" statements) run this protocol after drafting and before returning to the user. The independence trick: the verification questions are answered by an agent that never saw the draft. The full rule is `${CLAUDE_PLUGIN_ROOT}/rules/reference/post-flight-verification.md`; this page is the procedure a skill follows.

## The four steps

### Step 1: Draft

Produce the output as usual. Never skip post-flight because a draft looks obviously right.

### Step 2: Extract claims

List every assertion of these kinds:
- citation claims: "Author (Year) shows X";
- existence claims: "a dataset called X contains Y";
- numbers: counts, metrics, sample sizes, p-values;
- named entities: people, paper titles, venues, software and versions;
- negative literature claims: "no prior work studies X".

Skip opinions, suggestions and definitions the draft introduces itself.

### Step 3: Write verification questions

One specific, answerable question per claim, naming its source. "In <paper>, what sample size is reported in Table 2?" beats "Is <paper> about X?". Attach a source pointer to each: a bibliography entry, a local PDF path, a results file and key, a DOI or URL.

### Step 4: Answer in a fresh context, then reconcile

Spawn the `ploma:claim-verifier` agent (Agent tool, `subagent_type: ploma:claim-verifier`) with a prompt that holds **only** this block:

```yaml
source_material:
  - path: <file the claims can be checked against>
  - url: <DOI or canonical URL>
doi_lookup_cap: <optional; this verifier's share of limits.doi_lookups_per_run when several run in parallel>
claims:
  - id: C1
    text: "<the claim, one sentence>"
    source_hint: "<where the answer should be>"
    verification_question: "<the question from step 3>"
```

Never pass the draft, a summary of it, or the surrounding section. Do not paste the conversation. Isolation comes from what you put in the prompt; there is no fork parameter to rely on.

The verifier returns a report with a match value and a tier per claim. Map each claim first:

| Verifier result | Treatment |
|---|---|
| `yes`, no tier | verified |
| `partial` with no tier (a reasonable gloss of the source) | verified with a note; keep the claim and add an uncertainty flag inline saying what the source says exactly; does not change the outcome |
| `partial` or `cannot-verify` with LOW-WARN | advisory, non-gating; flag the claim inline as unverified, with the reason; does not change the outcome |
| `partial` or `cannot-verify` with MED-WARN | counts toward PARTIAL; flag the claim inline as unverified, with the reason |
| `no`, or any HIGH-WARN | counts toward FAIL |
| `not-verifiable-claim-type` | excluded from the claim count and from the outcome; listed under "Not verifiable (claim type)" with the verifier's one-line reason |

Then the outcome:

The outcome depends on the tier counts only:

- **PASS**: 0 HIGH-WARN and 0 MED-WARN, whatever the LOW-WARN count. LOW-WARN claims are listed as advisory and flagged inline. Return the draft.
- **PARTIAL**: 0 HIGH-WARN and at least one MED-WARN. Return the draft with each MED and LOW claim flagged inline.
- **FAIL**: at least one HIGH-WARN (a contradiction or a fabricated reference). Regenerate the affected section from the verifier's evidence and re-verify the changed claims. After the CoVe regeneration cap in limits (`limits.cove_regenerations`), stop and return the best draft with the remaining discrepancies in a warning block. Never ship a known-wrong claim silently.

## Output block

Every skill that runs this protocol ends its reply with:

```markdown
## Post-flight verification

**Claims extracted:** N (excluding not-verifiable claim types)
**Verified independently:** N (ploma:claim-verifier, fresh context)
**Outcome:** PASS | PARTIAL | FAIL, regenerated | FAIL, cap reached

### Verified

| ID | Claim | Evidence |
|---|---|---|
| C1 | <claim> | <source and location> |

### Unverifiable (user review recommended)

- **C4**: <reason, for example a paywalled source> (tier)

### Not verifiable (claim type)

- **C6**: <the verifier's one-line reason, for example "an opinion, not a factual assertion">

### Discrepancies

- **C3**: draft said "N = 10,000"; source says "N = 1,000". Corrected in the final output.
```

## Fail closed

If the verifier errors, times out or returns a report without the per-claim table, do not present the draft as checked. Say:

> Post-flight verification failed (<reason>). The draft has not been independently checked. Treat it as provisional.

and put the outcome as `FAIL, verifier error` in the output block. A missing verification is never a PASS.

## Opt-out

`--no-verify` skips post-flight. A skill that honours this protocol documents the flag in its argument hint, and when the flag is used its output block says `**Outcome:** skipped (--no-verify)`.
