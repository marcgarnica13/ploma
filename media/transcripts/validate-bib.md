> /ploma:validate-bib --semantic

[tool] Bash [ -d "$CLAUDE_PLUGIN_ROOT/scripts" ] && echo ok || echo missing

[tool] Bash ls /home/mgarnica/papers/scripts/validate_bib.py && python3 /home/mgarnica/paper

[tool] Bash python3 /home/mgarnica/papers/scripts/validate_bib.py --semantic --mailto ""

[tool] Read /home/mgarnica/ploma-demo-run/quality_reports/bib_audit_semantic.md

The semantic bibliography audit passed: all 7 cited entries were found in Crossref with exact title matches.

| Check | Critical | Medium | Low |
|---|---|---|---|
| Structural (missing / typos) | 0 | 0 | 0 |
| Citation drift (duplicates) | 0 | 0 | 0 |
| DOI verification | 0 | 0 | 0 |
| Style consistency | 0 | 0 | 0 |
| Unused entries | - | - | 0 (informational) |

**Verdict: PASS.** No missing citations, no unresolved problems.

- **FAIL / WARN:** none.
- **Existence checks:** the 7 entries are Wang2024, Park2023, Sambasivan2016, Kaldor2017, Mace2015, LasCasas2018 and LasCasas2019. None came back `partial`, `mismatch`, `unreachable` or `not_indexed`.
- **Unused entries:** 0. `refs.bib` has 7 entries and the paper cites all 7.
- **Contact address:** the plugin's Crossref contact setting (`crossref_mailto`) had no value, so the lookups ran without one. That didn't affect the result. Set it in the plugin options if you want lookups to use Crossref's faster "polite" service.

The full report is at `quality_reports/bib_audit_semantic.md`, and the script recorded the bib entry in the commit gate.

Bibliography clean. Run /ploma:compile if the bib file changed since the last build.
