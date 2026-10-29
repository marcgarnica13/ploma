---
type: llm
---

Pass only if every claim below holds for the final response:

1. It says in a sentence or two that ploma is a Claude Code plugin for LaTeX academic papers whose facts live in ploma.yaml.
2. It lists the installed skills: onboard, doctor, status, help, compile and validate-bib.
3. It names skills that are not installed yet (for example review, write, commit) and marks them as not yet installed or planned, without suggesting the user run them now.
4. It gives the install commands (marketplace add marcgarnica13/ploma, then /plugin install ploma@ploma) and the update command (/plugin marketplace update ploma, then /reload-plugins).
5. It is a short router, not a manual: it points to commands and does not explain their internals at length.
