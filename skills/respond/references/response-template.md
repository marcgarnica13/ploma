<!-- Ported from the traces harness respond-to-referees skill and the author's tracking draft format, which descend from pedrohcgs/claude-code-my-workflow (see UPSTREAMS.md). The source carries no attribution comment. -->

# Response template

`<outputs.dir>/response_to_referees.md` follows this layout. One `##` section per reviewer, one `### R{n}.{m}` entry per concern, the concern matrix at the end. Entries are keyed by id: a re-run finds an entry by its `### R{n}.{m}` heading and updates it in place.

```markdown
# Response to referees

**Paper:** "<document.title>"
**Venue:** <venue.profile or the venue the user names>
**Manuscript ID:** <from the reports or the user; "not given" otherwise>
**Response round:** <N>
**Date:** <YYYY-MM-DD>
**Reports:** <each report file, with the reviewer number read from its content>
**Revised manuscript:** <main file and the files it inputs>
**Checked against:** <"the submitted version at <ref> (--since)" or "Locations were not checked against the submitted version (no --since ref).">

## Cover letter

<One paragraph to the editor: thank the editor and the referees, name the main changes at a high level (two to four of them, each with its location), and say that a point-by-point response follows. No change is named here that the entries below do not support.>

## Reviewer <n> (<recommendation, verbatim, when stated>)

<One or two sentences thanking the referee for the specific points they raised.>

### R{n}.{m}: <short title>
<!-- ploma: source <report file>:<first line>-<last line> -->

- **Comment:** "<verbatim quote, 25 words or fewer>"
- **Severity:** major | minor | typo
- **Status:** Addressed | Partially addressed | Deferred | Disagreement | UNADDRESSED - REQUIRES AUTHOR INPUT
- **Location:** <file:line, section, table or figure in the revised manuscript; "none" when nothing changed>
- **Response:** <3 to 6 sentences: acknowledge, state the change or the reason for not changing, point to the location, optionally justify>

> ploma: <verifier evidence, only on a re-run when the evidence contradicts the author's Response>

<... one entry per concern ...>

## Concern matrix

| ID | Reviewer | Severity | Summary | Status | Location |
|---|---|---|---|---|---|
| R{n}.{m} | <n> | <severity> | <one-line summary> | <status> | <location> |
```

## Re-run rule

Entries are updated in place by id. Never rewrite an existing Response field: it may hold the author's words. A re-run changes only Status and Location of an existing entry, and when the verifier's evidence contradicts the author's text it adds `> ploma: <verifier evidence>` on its own line directly under the entry. Response text is drafted only for new entries and for entries still holding the UNADDRESSED placeholder. The `ploma: source` comment records where the concern sits in the report, so a re-run matches the concern by reviewer and source and keeps its id.

## Status labels

| Label | Meaning |
|---|---|
| Addressed | The revision resolves the concern with a specific change at a location that verifies. |
| Partially addressed | The revision moves in the requested direction but does not fully resolve it, or the claimed change could not be verified where the entry says. |
| Deferred | The manuscript does not change on this point and the response explains why (scope, a follow-up paper, conflicting referees). The reason comes from the author or an existing draft, never invented. |
| Disagreement | The authors respectfully keep their position; the response gives the reasoning and any compromise. The position comes from the author or an existing draft. |
| UNADDRESSED - REQUIRES AUTHOR INPUT | No evidence of a revision and no recorded decision to defer or disagree. The Response field says what the author must decide, and the entry is listed in the warning summary. |

An UNADDRESSED entry carries a placeholder response, never an invented one: "UNADDRESSED: <what is missing; for example, no second season or cross-validation split found in the revised manuscript>. Author input needed: revise, defer with a reason, or disagree with a reason."

## Matrix CSV

`<outputs.dir>/response_to_referees_matrix.csv` holds the same rows as the concern matrix, one per concern, with this header line:

```
id,reviewer,severity,summary,status,location
```

Quote every field that contains a comma or a quote mark (RFC 4180: double the inner quotes). The CSV is regenerated from the markdown matrix on every run, so the two never drift.

## Audit report

`--audit` writes `<outputs.dir>/response_audit.md` instead:

```markdown
# Response audit

**Draft:** <path>
**Reports:** <files, reviewer numbers>
**Date:** <YYYY-MM-DD>

## Result: <PASS | WARN | FAIL>: <C> of <N> concerns covered, <V> of <L> location claims verified

## Coverage

| ID | Concern (summary) | Covered in draft | Draft status | Consistent |
|---|---|---|---|---|

## Missing concerns

## Location claims

| Claim | Draft entry | Verdict | Evidence |
|---|---|---|---|

## Status inconsistencies

## Post-flight verification
```

Each problem under Missing concerns, Location claims and Status inconsistencies is a finding in the four-field format (location in the draft, the current text verbatim, the fix, the severity). An empty section says "None."
