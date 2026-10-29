---
paths:
  - "src/**/*.py"
  - "explorations/**"
---

# Research Project Orchestrator (Simplified)

**For Python pipeline scripts, discovery runs, and data analysis** -- use this simplified loop instead of the full multi-agent orchestrator.

## The Simple Loop

```
Plan approved → orchestrator activates
  │
  Step 1: IMPLEMENT — Execute plan steps
  │
  Step 2: VERIFY — Run code, check outputs
  │         Scripts: run from src/ (TAGS_FILE exported) without error
  │         Discovery: deterministic / seeded; node names contain `##`
  │         Figures: PNG/SVG created, correct pitch orientation
  │         No silent empty results on Mongo failure
  │         If verification fails → fix → re-verify
  │
  Step 3: SCORE — Apply quality-gates rubric
  │
  └── Score >= 80?
        YES → Done (commit when user signals)
        NO  → Fix blocking issues, re-verify, re-score
```

**No 5-round loops. No multi-agent reviews. Just: write, run, done.**

## Verification Checklist

- [ ] Script runs from `src/` without errors (`TAGS_FILE` exported before parser import)
- [ ] Explicit imports; no `from x import *`
- [ ] No hardcoded absolute paths / credentials; new deps pinned in `src/pyproject.toml` + `uv.lock` (`uv lock`)
- [ ] Randomness seeded (or determinism stated)
- [ ] `action##zone` activity-key format preserved; coordinate orientation correct
- [ ] Output files created at expected paths under `src/results/`
- [ ] Reproduction tolerance checks pass (if applicable)
- [ ] Quality score >= 80
