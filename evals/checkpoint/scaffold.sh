#!/usr/bin/env bash
# Stage a clean copy of the sample paper in the eval workspace (the current directory).
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
src="$here/../../examples/sample-paper"
cp -R "$src/." .
rm -rf .ploma quality_reports build main.pdf main.log main.aux main.bbl main.blg
# Onboarded state: the generated rules, CLAUDE.md section, outputs README, ledger, state and receipt.
python3 "$here/../../scripts/project_files.py" --root . apply >/dev/null
# One active plan, so the checkpoint has something to point at.
mkdir -p quality_reports/plans
cp "$here/fixtures/2026-10-28_tighten-evaluation.md" quality_reports/plans/
