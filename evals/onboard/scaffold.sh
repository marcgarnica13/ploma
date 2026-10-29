#!/usr/bin/env bash
# Stage a copy of the sample paper without ploma.yaml, so onboard runs as a first onboard.
set -euo pipefail
src="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/../../examples/sample-paper"
cp -R "$src/." .
rm -rf .ploma quality_reports build main.pdf main.log main.aux main.bbl main.blg
rm -f ploma.yaml
