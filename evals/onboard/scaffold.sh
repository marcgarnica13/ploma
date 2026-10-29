#!/usr/bin/env bash
# Stage a copy of the sample paper without ploma.yaml, so onboard runs as a first onboard.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
cp -R "$here/examples/sample-paper/." .
rm -f ploma.yaml
