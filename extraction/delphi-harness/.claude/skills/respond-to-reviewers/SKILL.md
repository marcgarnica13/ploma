---
name: respond-to-reviewers
description: Generate a structured response-to-reviewers document from a funder panel's critique and the revised proposal. Maps each panel comment to the specific revision, classifies coverage (addressed / partially / deferred / disagreement), and drafts polite but firm responses. Use during the resubmission stage of proposal revision.
argument-hint: "[panel-critique-path] [revised-proposal-path] [--no-verify]"
allowed-tools: ["Read", "Write", "Edit", "Grep", "Glob", "Bash", "Task"]
effort: high
---

# Respond to Reviewers

Produce a complete response-to-reviewers document by cross-referencing the funder panel's critique against the revised proposal. Classify every concern, draft a courteous response for each, and flag anything unaddressed before resubmission.

## Inputs

- `$0` — path to the panel critique / summary statement
- `$1` — path to the revised proposal

Supported formats and how to read them. In the commands below, `FILE` stands for the input path being converted — either `$0` (panel critique) or `$1` (revised proposal). Always use `mktemp` for the temp file (not a predictable `/tmp/...` name) so paths with spaces and concurrent runs don't collide, and so untrusted `FILE` paths can't clobber other temp files via symlink races.

| Format | How to extract text |
| --- | --- |
| `.tex`, `.md`, `.txt` | Read directly with the `Read` tool. |
| `.pdf` | `TMP=$(mktemp --suffix=.txt) && pdftotext "FILE" "$TMP"` (poppler-utils; use `mktemp -t ...` on macOS if `--suffix` is unsupported). Grep `"$TMP"`. |
| `.docx` | `TMP=$(mktemp --suffix=.txt) && pandoc "FILE" -t plain -o "$TMP"` (or `docx2txt "FILE" "$TMP"`). Grep `"$TMP"`. |
| `.html` | `TMP=$(mktemp --suffix=.txt) && pandoc "FILE" -t plain -o "$TMP"`. Grep `"$TMP"`. |

If a required tool is missing or extraction fails, ask the user to provide a plain-text version (`.txt` or `.md`) and stop.

## Workflow

### Step 0: Convert Inputs to Plain Text

Before any parsing or grep, convert non-text inputs (`.pdf`, `.docx`, `.html`) to plain text using the table above. Keep both the temp text file (for grep) and the original (for citation page references).

### Step 1: Parse the Panel Critique

1. Read the critique / summary statement end-to-end.
2. Decompose into discrete numbered concerns. Common patterns:
   - Numbered or bulleted enumerations ("1.", "(a)", "Comment 1", etc.).
   - Criterion headers ("Significance", "Approach", "Weaknesses").
   - Implicit concerns embedded in prose paragraphs — extract these too.
3. For each concern, capture:
   - **Concern ID** (P{n}.{m} = panelist n, comment m)
   - **Severity** the panelist assigned (major / minor / typographic)
   - **Verbatim quote** of the most representative sentence (~25 words max)
   - **One-line summary** in your own words

### Step 2: Locate Each Concern in the Revised Proposal

For every concern:

1. Extract the key terms from the panelist's wording.
2. `Grep` the **plain-text version** of the revised proposal for those terms (and synonyms). Note: Grep only works on text — if the original was any non-text format (for example, `.pdf`, `.docx`, or `.html`), grep the converted temp file from Step 0.
3. `Read` the surrounding context (±20 lines) to confirm the change addresses the concern.
4. Note the page/section/aim numbers in the **original** file (not the temp file) for the response document.

### Step 3: Classify Coverage

Assign one of four labels to each concern:

| Label | Meaning |
| --- | --- |
| **Addressed** | The revision directly resolves the concern with a specific change you can point to. |
| **Partially addressed** | The revision moves in the requested direction but does not fully resolve the concern (e.g., added one feasibility check when the panel asked for two). |
| **Deferred** | The revision does not change the proposal on this point but the response will explain why (out of scope, separate project, conflicting panelists, etc.). |
| **Disagreement** | The team respectfully disagrees with the panelist's premise. The response will explain the reasoning and any compromise. |

If you cannot find any evidence of a revision OR a deliberate decision to defer/disagree, mark the concern **UNADDRESSED — REQUIRES PI INPUT** and surface it in the warning summary at the end.

### Step 4: Draft Each Response

For every concern, write a 3–6 sentence response in this structure:

1. **Acknowledge** the concern (one sentence, no paraphrasing flattery).
2. **State the change** (or the reason for not changing).
3. **Point to the location** in the revised proposal (page, section, aim range, or table/figure number).
4. **(Optional) Justify** the choice if the change diverges from the panelist's exact ask.

Tone conventions: courteous but firm; never defensive; never quote the panelist back at length; use "we" for the team; avoid "the panelist is wrong" — prefer "we respectfully retain our original framing because…".

### Step 5: Produce the Response Document

Write the output to `response-to-reviewers.md` (matching the template filename) or a path the user specifies. Use the structure in `templates/response-to-reviewers.md`:

1. **Header** — funder / program, proposal ID, resubmission round, date.
2. **Cover paragraph** — one paragraph thanking the program officer and panel, summarizing the major changes at a high level.
3. **Per-panelist sections** — for each panelist, a numbered list of responses produced in Step 4.
4. **Concern matrix** — at the end, a single table summarizing every concern, classification, and response location for program-officer convenience.

### Step 5.5: Post-Flight Verification (MANDATORY, CoVe)

The response document's most hallucination-prone content is the set of "we added X on page Y" claims. Hallucinating these gets a resubmission flagged on sight. Before declaring the response document final, run the Post-Flight Verification protocol from [`.claude/rules/post-flight-verification.md`](../../rules/post-flight-verification.md).

**Steps:**

1. **Extract revision-location claims** — every "we added / we modified / we revised X (page Y, line Z / Section N / Aim K)" assertion in the response document.
2. **Generate verification questions** — "Does the revised proposal actually contain the revision claimed at page Y, line Z? Does it match the description?"
3. **Spawn `claim-verifier`** via `Task` with `subagent_type=claim-verifier` and `context=fork`. Hand it: the claims table, the verification questions, the path to the revised proposal. Do NOT include the response draft.
4. **Reconcile:** PASS → attach green block. PARTIAL / FAIL → rewrite the affected response entries using the verifier's evidence. A response that says "we added feasibility check X on page 8" when X is actually on page 6 (or not at all) is worse than a "Deferred" classification.

Downgrade to the classification the evidence supports:

- Claim verified at location → `Addressed`
- Claim verified at different location → update the location in the response
- Claim not verifiable in proposal → downgrade to `Partially addressed` or `Deferred` with an honest rationale

Opt-out: `--no-verify` flag. Not recommended — the panel will run this check themselves.

### Step 6: Warning Summary (MANDATORY)

After the document is written, include this summary in your **final chat message to the user** (NOT inside the response document):

```
## Unaddressed concerns requiring PI input

- P1.3: [summary] — no evidence of revision found
- P2.7: [summary] — flagged as deferred but no rationale yet drafted
```

If everything is covered, the final message should say `All concerns addressed or explicitly classified.`

## Output Files

- `response-to-reviewers.md` — the deliverable (filename matches `templates/response-to-reviewers.md`)
- (Optional) `response-to-reviewers-matrix.csv` — machine-readable concern-to-response mapping for tracking across resubmissions

## Pre-submission rehearsal

**Tip.** Before drafting your response, consider running `/review-proposal --panel --r2 <funder>` on the *revised* proposal first. It simulates the next panel round against your revisions — catching the "Resolved / Partial / Not addressed" classification mistakes before the real panel does. See [`.claude/skills/review-proposal/SKILL.md`](../review-proposal/SKILL.md).

## Cross-References

- For first-pass proposal review **before** receiving a panel critique, use `/review-proposal`.
- For substantive content audits during revision, use `/seven-pass-review` (or the `domain-reviewer` agent directly) on the `.tex` proposal.
- Save the response to `quality_reports/` if you want a permanent record alongside other quality reports.

## Verification

Before reporting completion:

1. Confirm every concern has a classification (no orphans).
2. Confirm every "Addressed" or "Partially addressed" classification cites a specific page/section/aim.
3. Confirm the warning summary was emitted (even if empty).
4. Confirm the cover paragraph names the funder / program and proposal ID correctly.
