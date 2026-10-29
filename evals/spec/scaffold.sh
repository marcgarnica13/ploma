#!/usr/bin/env bash
# Stage a clean copy of the sample paper in the eval workspace (the current directory).
set -euo pipefail
src="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/../../examples/sample-paper"
cp -R "$src/." .
rm -rf .ploma quality_reports build main.pdf main.log main.aux main.bbl main.blg
# One earlier grill decision log, so the spec pre-fills its locked decisions from it.
mkdir -p quality_reports/decisions
cp "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/fixtures/2026-10-20_evaluation.md" quality_reports/decisions/
