---
type: llm
---

Pass only if every claim below holds for the run:

1. A checkpoint file was written under quality_reports/checkpoints/ with a date and the slug evaluation-pass in its name, and the reply names that path.
2. The checkpoint's frontmatter names the plan quality_reports/plans/2026-10-28_tighten-evaluation.md and a status.
3. The checkpoint has a goal, where things stand, file pointers, open questions (including the appendix question from the plan) and one to three next actions, and is under about 80 lines.
4. Missing inputs (no session log, no git repository) are recorded as none rather than invented.
5. If learnings are proposed, none is appended to quality_reports/learnings.md without the user's yes, and there are at most three.
6. No .tex, .bib or ploma.yaml file was created or changed.
