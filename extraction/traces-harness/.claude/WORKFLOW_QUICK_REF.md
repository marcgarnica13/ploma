# Workflow Quick Reference

**Model:** Contractor (you direct, Claude orchestrates)

---

## The Loop

```
Your instruction
    ↓
[PLAN] (if multi-file or unclear) → Show plan → Your approval
    ↓
[EXECUTE] Implement, verify, done
    ↓
[REPORT] Summary + what's ready
    ↓
Repeat
```

---

## I Ask You When

- **Design forks:** "Option A (fast) vs. Option B (robust). Which?"
- **Code ambiguity:** "Spec unclear on X. Assume Y?"
- **Reproduction edge case:** "Fitness just missed tolerance. Investigate?"
- **Scope question:** "Also refactor Y while here, or focus on X?"

---

## I Just Execute When

- Code fix is obvious (bug, pattern application)
- Verification (reproduction tolerance checks, pdflatex build, pipeline run)
- Documentation (logs, commits)
- Pitch figures (per established viz standards)

---

## Quality Gates (No Exceptions)

| Score | Action |
|-------|--------|
| >= 80 | Ready to commit |
| < 80  | Fix blocking issues |

See `.claude/rules/quality-gates.md`.

---

## Non-Negotiables (this project's locked conventions)

- **Run Python scripts from `src/`**, and **export `TAGS_FILE` before importing the parser**
  (`src/sports_pm/parsers/soccerlogs.py` reads `os.environ['TAGS_FILE']` at import time).
- **Preserve the `action##zone` activity-key format** — `create_event_log` emits
  `"{action_id|sub_action_id}##{key_zone}"`; consumers split on `"##"`.
- **Verify pitch coordinate orientation** when touching viz/zone math (the `y -> FIELD_WIDTH - y`
  flip); zone on standardized 105×68 coordinates, not raw.
- **Build the manuscript via `cd manuscript && make`** (pdflatex → bibtex → pdflatex ×2, **not
  xelatex**). Output: `manuscript/samplepaper.pdf`.
- **Keep authors anonymized** in `samplepaper.tex` until a non-blind submission.
- **Pin dependencies** in `src/requirements.txt` (pm4py 2.3.1, pandas 1.5.2, …).
- **Env-var contract:** `MONGO_USER`, `MONGO_PWD`, `MONGO_STR`, `TAGS_FILE`, `RESULTS_FILE`. No
  hard-coded paths or credentials. Fail loudly when Mongo is unreachable.

---

## Preferences

<!-- Fill in as you discover your working style -->

**Visual:** [How you want pitch figures handled]
**Reporting:** [Concise bullets? Detailed prose? Details on request?]
**Session logs:** Always (post-plan, incremental, end-of-session)
**Reproduction:** [How strict? Flag near-misses? Mongo-snapshot caveats?]

---

## Exploration Mode

For experimental work, use the **Fast-Track** workflow:
- Work in `explorations/` folder
- 60/100 quality threshold (vs. 80/100 for production)
- No plan needed — just a research-value check (2 min)
- See `.claude/rules/exploration-fast-track.md`

---

## Next Step

You provide task → I plan (if needed) → Your approval → Execute → Done.
