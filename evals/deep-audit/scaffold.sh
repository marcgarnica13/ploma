#!/usr/bin/env bash
# Stage a clean copy of the sample paper in the eval workspace (the current directory).
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
src="$here/../../examples/sample-paper"
cp -R "$src/." .
rm -rf .ploma quality_reports build main.pdf main.log main.aux main.bbl main.blg
# Onboarded state: the generated rules, CLAUDE.md section, outputs README, ledger, state and receipt.
python3 "$here/../../scripts/project_files.py" --root . apply >/dev/null
# Two seeded problems: a hand-written project rule that restates the page budget and names a missing
# script, and a report that cites a file that no longer exists.
mkdir -p .claude/rules
cp "$here/fixtures/project-notes.md" .claude/rules/project-notes.md
cp "$here/fixtures/old_review_notes.md" quality_reports/old_review_notes.md
