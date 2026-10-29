# Post-flight verification (Chain-of-Verification)

Pre-flight proves the inputs were read before work. Post-flight proves the factual claims of a draft hold after drafting, before a skill returns to the user.

Adapted from Dhuliawala et al. 2023, "Chain-of-Verification Reduces Hallucination in Large Language Models" (arXiv:2309.11495). The independence trick: verification questions are answered in a context that never saw the draft.

## When this rule applies

Any skill whose output holds claims that can be checked against a source:

| Skill | High-risk claims |
|---|---|
| `/ploma:lit-review` | a paper exists; authors, year, venue; paraphrased findings |
| `/ploma:brainstorm` | "no prior work studies X"; dataset structure; method feasibility |
| `/ploma:spec` | papers cited in the spec |
| `/ploma:respond` | "we added X on page Y" statements about the revision |
| `/ploma:review --peer` | novelty claims from web search |

It does not apply to mechanical skills (`/ploma:compile`, `/ploma:commit`); an external process verifies their output.

## The four steps

1. **Draft.** Produce the output as usual. Never skip post-flight because a draft looks obviously right.
2. **Extract claims.** Citation claims ("Author (Year) shows X"), existence claims, numbers, named entities, negative literature claims. Skip opinions, suggestions and definitions the draft introduces itself.
3. **Write verification questions.** One specific, answerable question per claim, naming its source. "In <paper>, what sample size is reported in Table 2?" beats "Is <paper> about X?".
4. **Answer in a fresh context, then reconcile.** Dispatch the `ploma:claim-verifier` agent with the claims, the questions and pointers to the sources. Never pass the draft.

Outcomes:

- **PASS**: every claim matches. Return the draft.
- **PARTIAL**: some claims cannot be verified, none contradicted. Return the draft with each unverified claim flagged.
- **FAIL**: a claim contradicts its source. Regenerate the affected section from the verifier's evidence. After `limits.cove_regenerations` attempts (default 2), return the best draft with the discrepancies in a warning block. Never ship a known-wrong claim silently.

## Output contract

```markdown
## Post-flight verification

**Claims extracted:** N
**Verified independently:** N (claim-verifier, fresh context)
**Outcome:** PASS | PARTIAL | FAIL, regenerated

| ID | Claim | Evidence |
|---|---|---|

### Unverifiable (user review recommended)
- C4: reason

### Discrepancies (regenerated)
- C3: draft said "N = 10,000"; source says "N = 1,000". Corrected.
```

## Fail closed

If the verifier errors, times out or returns malformed output, do not ship the draft as checked. Say: "Post-flight verification failed (reason). The draft has not been independently checked. Treat it as provisional."

## Opt-out

`--no-verify` skips post-flight. Each skill that honours this rule documents the flag.
