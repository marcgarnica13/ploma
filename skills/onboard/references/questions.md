# Turning inventory gaps into AskUserQuestion questions

`inventory.py --json gaps` returns a list of `{key, question, recommended, options}`. Each gap becomes one question. `AskUserQuestion` takes one to four questions per call and two to four options per question; the user can always type another answer.

Rules for every question:

- The recommended option comes first and its label ends with "(Recommended)".
- The question stands on its own: name the file, class or directory it is about. Never "the one above".
- `header` is a short tag (at most 12 characters): `Main file`, `Venue`, `Page budget`, `Discipline`, `Pipeline`, `Metrics`.
- Each option's description says what choosing it writes into `ploma.yaml`.

Per gap key:

| key | options | writes |
|---|---|---|
| `document.main` | the candidates, recommended first; more than four: the recommended one plus the three with the most `\input` lines | `document.main` (asked alone, before the others) |
| `venue.profile` | `options` in order, recommended first, at most four | `venue.profile` |
| `venue.page_budget` | recommended budget (when not null) first, then "No page budget"; when the recommendation is null, "No page budget (Recommended)" first and the chosen venue's budget from `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/profiles.py" --root . show <profile>` (`--root .` so `ploma.d/` overrides are found) if it has one. Each budget option names its `includes_refs` choice: "N pages, references do not count toward the limit (Recommended)" first, then "N pages, references count toward the limit" | `venue.page_budget` (a number, or null) and `venue.page_budget_includes_refs` (from the gap's `includes_refs`: false unless the user picks "references count toward the limit") |
| `document.discipline` | `options` in order (the shipped and `ploma.d/` discipline keys), recommended first, at most four. The recommendation is `ml` for an ML venue (`springer-ml`, `llncs-conference`, or a venue name containing learning, neurips, icml or iclr) or a Python code tree with a results directory, else `generic` | `document.discipline` |
| `pipeline.enabled` | "Yes, it produces the numbers" and "No, unrelated code", recommended first | `pipeline.enabled`; on No, drop the whole `pipeline` block |
| `pipeline.metric_keys` | multiSelect; up to four keys from `options`; more than four: "All N keys (Recommended)" and "None for now", and the user may type a list. Empty `options` (no key looked like a metric): "None for now (Recommended)" and "I will type them" | `pipeline.metric_keys` |

When the user picks a venue other than the recommended one in the same call, and the page budget answer was the recommended venue's default, use the chosen venue's `page_budget` instead and say so. Likewise, when the recommended discipline was `ml` only because of the recommended venue and the user picks a venue that is not an ML venue (and no Python pipeline with results exists), use `generic` and say so; picking an ML venue turns a recommended `generic` into `ml`.

A gap with no options and a null recommendation, other than `document.main`, gets two options: "Leave unset (Recommended)" and "I will type it". `document.main` is never left unset: with no candidates, onboard stops and asks the user to name the main file (SKILL.md step 3).
