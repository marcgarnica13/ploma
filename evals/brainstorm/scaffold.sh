#!/usr/bin/env bash
# Stage a clean copy of the sample paper in the eval workspace (the current directory).
set -euo pipefail
src="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/../../examples/sample-paper"
cp -R "$src/." .
rm -rf .ploma quality_reports build main.pdf main.log main.aux main.bbl main.blg
