---
type: llm
---

Pass only if every claim below holds for the final response:

1. It quotes the inventory output (JSON) as its record of what was detected.
2. It shows a full proposed ploma.yaml in YAML with document.main set to main.tex, build.engine pdflatex, build.bib_tool bibtex and refs.bib as the bibliography file.
3. It raises the venue profile as an open question with a recommended option listed first (generic-journal for the article class), and the page budget as a question; it does not ask about anything the inventory already detected (main file, engine, bib tool, build command).
4. It shows a plan table of project files with path, mode and action columns, including .claude/rules/ploma-manuscript.md.
5. It shows the .claude/settings.json suggestion as something the user applies themselves.
6. It states that this was a dry run and nothing was written.
