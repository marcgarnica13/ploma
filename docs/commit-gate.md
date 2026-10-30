# Commit gate

What `/ploma:commit` checks before it commits, and how to override it. Changes to the gate are listed in [CHANGELOG.md](../CHANGELOG.md).

## Required and recommended checks

`/ploma:commit` refuses to commit until the required checks have passed on the current files. It refreshes missing or stale `compile`, `bib` (structural) and `consistency` entries itself before it decides.

- Required: `compile` and `bib` (written by `/ploma:compile` and `/ploma:validate-bib`).
- Recommended: `consistency`, `claims`, `proofread`. `consistency` is recommended today and becomes required in a later release.

## Overrides

- Override: write `commit anyway: <reason>` on its own line in your message. The reason is logged. After three consecutive overridden commits the gate stops accepting overrides until the required checks pass.

## Checking the gate

`python3 scripts/gate.py check` shows the gate state without committing.
