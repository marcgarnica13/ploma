---
paths:
  - "drafts/**"
---

# Draft Folder Protocol

**All exploratory drafting goes into `drafts/` first.** Never directly into the proposal.

## Folder Structure

```
drafts/
├── ACTIVE_DRAFTS.md
├── [draft]/
│   ├── README.md          # Goal, status, findings
│   ├── notes/             # Working notes (use _v1, _v2 for iterations)
│   ├── output/            # Drafted text / figures
│   └── SESSION_LOG.md     # Progress notes
└── ARCHIVE/
    ├── completed_[draft]/
    └── abandoned_[draft]/
```

## Lifecycle

1. **Create** -- `mkdir -p drafts/[name]/{notes,output}` + a short README
2. **Develop** -- work entirely within the draft folder
3. **Decide:**

   - **Graduate into the proposal** -- fold the text/figures into `proposal/proposal_a4.tex` (or `proposal/proposal_slides.tex`); requires quality >= 80, manual review, prose clear. Move to `ARCHIVE/completed_[draft]/`
   - **Keep drafting** -- document next steps in README
   - **Abandon** -- move to `ARCHIVE/abandoned_[draft]/` with explanation (use `templates/archive-readme.md`)

## Graduate Checklist

- [ ] Quality score >= 80
- [ ] Manual review done (proposal still compiles, prose reads cleanly)
- [ ] Claims supported and citations resolve
- [ ] Text is clear without deep context; consistent with the rest of the proposal
- [ ] README explains approach and findings
