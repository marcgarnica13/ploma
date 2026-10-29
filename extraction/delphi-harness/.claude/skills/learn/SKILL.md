---
name: learn
description: |
  Extract reusable knowledge from the current session into a persistent skill.
  Use when you discover something non-obvious, create a workaround, or develop
  a multi-step workflow that future sessions would benefit from.
author: Claude Code Academic Workflow
version: 1.0.0
argument-hint: "[skill-name (kebab-case)]"
allowed-tools: ["Read", "Write", "Bash", "Glob", "Grep"]
disable-model-invocation: true
---

# /learn — Skill Extraction Workflow

Extract non-obvious discoveries into reusable skills that persist across sessions.

## When to Use This Skill

Invoke `/learn` when you encounter:

- **Non-obvious debugging** — Investigation that took significant effort, not in docs
- **Misleading errors** — Error message was wrong, found the real cause
- **Workarounds** — Found a limitation with a creative solution
- **Tool integration** — Undocumented API usage or configuration
- **Trial-and-error** — Multiple attempts before success
- **Repeatable workflows** — Multi-step task you'd do again
- **User-facing automation** — Reports, checks, or processes users will request

## Workflow Phases

### PHASE 1: Evaluate (Self-Assessment)

Before creating a skill, answer these questions:

1. "What did I just learn that wasn't obvious before starting?"
2. "Would future-me benefit from this being documented?"
3. "Was the solution non-obvious from documentation alone?"
4. "Is this a multi-step workflow I'd repeat?"

**Continue only if YES to at least one question.**

### PHASE 2: Check Existing Skills

Search for related skills to avoid duplication:

```bash
# Check project skills
ls .claude/skills/ 2>/dev/null

# Search for keywords
grep -r -i "KEYWORD" .claude/skills/ 2>/dev/null
```

**Outcomes:**
- Nothing related → Create new skill (continue to Phase 3)
- Same trigger & fix → Update existing skill (bump version)
- Partial overlap → Update with new variant

### PHASE 3: Create Skill

Create the skill file at `.claude/skills/[skill-name]/SKILL.md`:

```yaml
---
name: descriptive-kebab-case-name
description: |
  [CRITICAL: Include specific triggers in the description]
  - What the skill does
  - Specific trigger conditions (exact error messages, symptoms)
  - When to use it (contexts, scenarios)
author: Claude Code Academic Workflow
version: 1.0.0
argument-hint: "[expected arguments]"  # Optional
---

# Skill Name

## Problem
[Clear problem description — what situation triggers this skill]

## Context / Trigger Conditions
[When to use — exact error messages, symptoms, scenarios]
[Be specific enough that you'd recognize it again]

## Solution
[Step-by-step solution]
[Include commands, code snippets, or workflows]

## Verification
[How to verify it worked]
[Expected output or state]

## Example
[Concrete example of the skill in action]

## References
[Documentation links, related files, or prior discussions]
```

### PHASE 4: Quality Gates

Before finalizing, verify:

- [ ] Description has specific trigger conditions (not vague)
- [ ] Solution was verified to work (tested)
- [ ] Content is specific enough to be actionable
- [ ] Content is general enough to be reusable
- [ ] No sensitive information (credentials, personal data)
- [ ] Skill name is descriptive and uses kebab-case

## Output

After creating the skill, report:

```
✓ Skill created: .claude/skills/[name]/SKILL.md
  Trigger: [when to use]
  Problem: [what it solves]
```

## Example: Creating a Skill

User discovers that the proposal PDF silently overflows the funder's page limit
unless a specific class option is set:

```markdown
---
name: a4-page-budget-guard
description: |
  Guard against the proposal exceeding the funder's hard page limit.
  Use when: the built PDF runs longer than the call allows, or a section
  reflows onto an extra page after an edit.
author: grant project
version: 1.0.0
---

# A4 Page-Budget Guard

## Problem
The funder caps the project description at a fixed page count. The LaTeX
class silently lets content overflow — `cd proposal && make all` produces a
PDF without warning, and the overflow is only caught on visual page count.

## Context / Trigger Conditions
- The built PDF exceeds the call's page limit
- A section reflows onto an extra page after adding text or a figure
- The funder's formatting rules (margins, font size) are not enforced by the class

## Solution
1. Build the proposal and check the page count immediately after each edit:
   ```bash
   cd proposal && make all
   ```
2. Keep margin/font settings pinned to the funder's required values in the preamble.
3. Add a final-page-count check to the pre-submission checklist; trim or move
   content to an appendix rather than shrinking margins.

## Verification
Build `proposal/proposal_a4.tex` and confirm the page count is at or under the
funder's limit with the required margins and font size intact.

## References
- The funder's formatting rules in `funder-profiles.md`
- [LEARN:formatting] entry in MEMORY.md
```
