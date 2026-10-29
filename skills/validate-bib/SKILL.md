---
name: validate-bib
description: Audit the paper's bibliography and record the bib entry of the commit gate. Structural mode checks every cited key against the bib files (missing keys, near-miss typos, duplicates, unused entries, mixed citation packages). Semantic mode also checks that each cited entry exists on Crossref, DataCite, OpenAlex or Semantic Scholar. Use when the user asks to check, validate or audit the bibliography, references or citations, after undefined citations in a compile, or before a commit.
argument-hint: "[--semantic] [--skip-doi]"
allowed-tools: Read, Glob, Grep, Bash(python3 *)
---

# ploma validate-bib

Arguments: `$ARGUMENTS`. `--semantic` adds the existence lookups (network, at most `limits.doi_lookups_per_run` per run, cached for 90 days). `--skip-doi` with `--semantic` makes no lookups.

No `ploma.yaml` in the repo root: say "ploma is not set up here. Run /ploma:onboard." and stop.

Report-only: this skill never edits a `.bib` or `.tex` file. It names each fix; the user applies it.

If the arguments contain `--cite-claim`: claim checks belong to `/ploma:verify-claims`. Say so in one line, then run the bibliography audit without that flag.

## 1. Run

Structural (no arguments):

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/validate_bib.py"
```

Semantic: add `--semantic`, plus `--skip-doi` when the arguments contain it, plus the contact address for the polite pools:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/validate_bib.py" --semantic --mailto "${user_config.crossref_mailto}"
```

Run the semantic command with a Bash timeout of 600000 ms (ten minutes): a large bibliography takes minutes. The script stops making lookups after 480 s, saves what it found, and reports how many cited entries it skipped; run it again to check those (results already found are cached).

Pass nothing else from the arguments. An empty mailto is ignored by the script. The OpenAlex and Semantic Scholar API keys are read by the script from the plugin's configured options; never type them into the conversation or the command.

Exit 0 is verdict PASS, exit 1 is verdict FAIL (a result, not an error), exit 2 is a usage error, an unreadable `ploma.yaml` or a missing main file: quote the message and stop.

The script prints the summary table, the verdict line and the report path (`<outputs.dir>/bib_audit_structural.md` or `bib_audit_semantic.md`). It has already recorded the gate entry and the state event. Do not record them again.

## 2. Report

1. Quote the summary table and the `**Verdict:**` line exactly as printed.
2. Read the report. Under the table, one line per FAIL, in report order: the key, where it is cited (the Observed text), and the fix. For a missing key with a near-miss WARN, give the near-miss key as the fix ("cite `Elo1978`, not `elo1978`").
3. Then one line per WARN with its fix. A lookup that was `unreachable` concluded nothing; say so, and never call that entry wrong. A `not_indexed` entry was not found in the citation indexes, which is normal for reports, preprints, software and web pages; ask the user to confirm it exists, never call it fabricated.
4. In semantic mode, say how many cited entries were verified and name any `partial` or `mismatch` entries with the evidence from the DOI table.
5. Unused entries and entries without a DOI: one line with the counts. Do not list them unless asked.

## 3. Next step

End with one line, the first that applies:

- verdict FAIL: "Fix the FAIL entries above, then run /ploma:validate-bib again."
- structural PASS: "Structural check clean. Run /ploma:validate-bib --semantic before submission to check the entries exist."
- semantic PASS: "Bibliography clean. Run /ploma:compile if the bib file changed since the last build."
