> /ploma:onboard --yes

[tool] Bash ls $CLAUDE_PLUGIN_ROOT/scripts >/dev/null 2>&1 && echo plugin_ok; python3 "/home

[tool] Bash python3 /home/mgarnica/papers/scripts/host.py --json; ls -la; git status --short

[tool] Read /home/mgarnica/ploma-demo-run/ploma.yaml

[tool] Bash ls -la .ploma results sections; cat .gitignore

Absorption run (document.type is `paper`). Running the inventory with `--main main.tex`.

[tool] Bash S=/home/mgarnica/papers/scripts; echo "=== inventory"; python3 $S/inventory.py -

[tool] Bash echo "=== inventory"; python3 /home/mgarnica/papers/scripts/inventory.py --json

[tool] Bash echo "=== switch"; python3 /home/mgarnica/papers/scripts/project_files.py --host

[tool] Bash python3 /home/mgarnica/papers/scripts/project_files.py --host claude --json swit

[tool] Bash python3 /home/mgarnica/papers/scripts/project_files.py --host claude --config -

[tool] Bash python3 /home/mgarnica/papers/scripts/project_files.py --host claude --config -

[tool] Bash python3 /home/mgarnica/papers/scripts/project_files.py --config - statusline <<'

Now the write. I add the one missing key with Edit, then apply.

[tool] Edit /home/mgarnica/ploma-demo-run/ploma.yaml

[tool] Bash python3 /home/mgarnica/papers/scripts/project_files.py --host claude --json appl

[tool] Bash python3 /home/mgarnica/papers/scripts/doctor.py; echo "=== next"; python3 /home/

Onboarding for Claude Code

## 0. Host
```json
{"name": "claude", "display": "Claude Code", "skill_prefix": "/ploma:", "instructions_file": "CLAUDE.md",
 "host_dir": ".claude", "rules_dir": ".claude/rules", "project_skills_dir": ".claude/skills", "agents_dir": null,
 "root_export": null, "learnings_target": ".claude/rules/ploma-learnings.md",
 "settings_suggestion": true, "statusline": true, "plugin_link": "/home/mgarnica/papers"}
```

## 1. Route
`ploma.yaml` already exists and `document.type: paper`, so this run adds to the existing file rather than starting fresh. Keys you already set are kept as they are.

## 2. Inventory
```json
{"main_candidates": ["main.tex"], "main": "main.tex", "doc_class": "article", "doc_class_options": ["11pt"],
 "engine_hint": "pdflatex", "bib_tool": "bibtex", "bib_files": ["refs.bib"],
 "build": {"kind": "make", "command": "make", "cwd": ".", "main_from_makefile": "main"},
 "pdf": "main.pdf", "pdf_pages": null, "title": "Tracing Agentic Workloads at Scale", "anonymized": false,
 "figures": [], "uses_author_year": false, "reviews_dir": null, "results_dir": "results", "code": null,
 "git_remote": null, "superpowers": {"enabled": true, "id": "superpowers@claude-plugins-official"},
 "legacy_harness": []}
```

## 3. Main file
`main.tex` was found without ambiguity, so there was no question to ask.

## 4. Gaps
```json
[{"key": "venue.profile", "recommended": "generic-journal", "options": ["generic-journal","generic-conference","arxiv"]},
 {"key": "venue.page_budget", "recommended": null, "includes_refs": {"recommended": false}},
 {"key": "document.discipline", "recommended": "generic", "options": ["generic","ml","social-science"]}]
```
(`propose` output: the detected YAML. The table below compares it with your file.)

| key | ploma.yaml | detected | result |
|---|---|---|---|
| venue.profile | generic-conference | generic-journal | yours kept |
| venue.page_budget | 10 | null | yours kept |
| document.discipline | *(missing)* | generic | **added: `generic` (assumed)** |
| all other keys | present | match | unchanged |

There was no way to ask questions in this session, so `document.discipline` took its recommended value and is marked assumed.

## 5. Legacy harness
`legacy_harness: []`, so there is nothing to retire.

## 6. Proposal
Switch check:
```json
{"notice": null}
```
The proposal is your current `ploma.yaml` plus one line, `discipline: generic`, under `document:`.

Plan (`withheld: []`):

| path | mode | action |
|---|---|---|
| .claude/rules/ploma-manuscript.md | enforced | create |
| .claude/rules/ploma-pipeline.md | enforced | create |
| quality_reports/README.md | created-once | create |
| quality_reports/learnings.md | created-once | create |
| quality_reports/ploma-state.yaml | created-once | create |
| .claude/skills/analysis-pipeline/SKILL.md | created-once | create |
| CLAUDE.md | merged | create |
| .gitignore | merged | merge |

Diff of the merge row:
```diff
--- a/.gitignore
+++ b/.gitignore
@@ -5,3 +5,7 @@
 *.log
 *.out
 main.pdf
+# ploma
+.ploma/
+quality_reports/session_logs/
+quality_reports/.cache/
```

`.claude/skills/analysis-pipeline/SKILL.md` is a project skill for running and extending the analysis pipeline. It is written once and is then yours to edit. `pipeline.stages` is unset, so the skill says "Stage chain: not declared". You could add the ordered stage names to `ploma.yaml`.

Settings suggestion for `.claude/settings.json`:
```json
{"plansDirectory": "quality_reports/plans",
 "permissions": {"allow": ["Bash(make:*)","Bash(pdfinfo:*)","Bash(pdftotext:*)","Bash(chktex:*)",
                           "Bash(lacheck:*)","Bash(texcount:*)","Bash(python3 *)"]}}
```
Plugins cannot grant permissions, so add this yourself if you want it.

There is also an optional status line script (`project_files.py statusline`). It shows the permission mode, model, branch and ploma stage. Its header says to save it to `.claude/statusline.sh` and to enable it with `"statusLine": {"type": "command", "command": "bash .claude/statusline.sh"}`. I did not write it.

`--yes` was given, so I skipped the approval question.

## 7. Write
1. I used Edit to add `discipline: generic` under `document:` in `ploma.yaml`. Your comments and key order are unchanged.
2. Apply. Each row matches the plan above (the diffs are the same, so they are left out here):
```json
[{"path": ".claude/rules/ploma-manuscript.md", "mode": "enforced", "action": "create", "written": true},
 {"path": ".claude/rules/ploma-pipeline.md", "mode": "enforced", "action": "create", "written": true},
 {"path": "quality_reports/README.md", "mode": "created-once", "action": "create", "written": true},
 {"path": "quality_reports/learnings.md", "mode": "created-once", "action": "create", "written": true},
 {"path": "quality_reports/ploma-state.yaml", "mode": "created-once", "action": "create", "written": true},
 {"path": ".claude/skills/analysis-pipeline/SKILL.md", "mode": "created-once", "action": "create", "written": true},
 {"path": "CLAUDE.md", "mode": "merged", "action": "create", "written": true},
 {"path": ".gitignore", "mode": "merged", "action": "merge", "written": true}]
```
3. `.ploma/plugin` was refreshed. It links to `/home/mgarnica/papers`, which is how hooks and agents find the scripts. The receipt is at `quality_reports/ploma-receipt.json`.

## 8. Verify
```
Overall verdict: READY_WITH_WARNINGS
Counts: PASS 20 WARN 2 FAIL 0 INFO 4 SKIP 5
- WARN config.path.reviews.glob: reviews.glob points into a directory that does not exist
  Observed: review
  Remediation: Create the reviews directory when referee reports arrive, or fix or remove reviews.glob in ploma.yaml.
- WARN manuscript.pdf_stale: no compiled PDF
  Observed: missing: main.pdf
  Remediation: Run /ploma:compile
```
```
compile: no lifecycle stage recorded yet; start by compiling
```

Verdict: READY_WITH_WARNINGS. There are no failures; the two warnings are the missing `review/` directory and the PDF that hasn't been built yet.

Next: /ploma:compile
