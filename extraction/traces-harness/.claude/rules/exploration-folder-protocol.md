---
paths:
  - "explorations/**"
---

# Exploration Folder Protocol

**All experimental work goes into `explorations/` first.** Never directly into production folders.

## Folder Structure

```
explorations/
├── ACTIVE_PROJECTS.md
├── [project]/
│   ├── README.md          # Goal, status, findings
│   ├── R/                 # Code (use _v1, _v2 for iterations)
│   ├── scripts/           # Test scripts
│   ├── output/            # Results
│   └── SESSION_LOG.md     # Progress notes
└── ARCHIVE/
    ├── completed_[project]/
    └── abandoned_[project]/
```

## Lifecycle

1. **Create** -- `mkdir -p explorations/[name]/{src,output}` + a short README
2. **Develop** -- work entirely within the exploration folder
3. **Decide:**

   - **Graduate to production** -- copy into `src/sports_pm/` (or `src/notebooks/`); requires quality >= 80, manual verification, code clear. Move to `ARCHIVE/completed_[project]/`
   - **Keep exploring** -- document next steps in README
   - **Abandon** -- move to `ARCHIVE/abandoned_[project]/` with explanation (use `templates/archive-readme.md`)

## Graduate Checklist

- [ ] Quality score >= 80
- [ ] Manual verification done (no test suite — runs cleanly from `src/`, outputs sane)
- [ ] Results reproduce within tolerance
- [ ] Code is clear without deep context; respects the project gotchas
- [ ] README explains approach and findings
