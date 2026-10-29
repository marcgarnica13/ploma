#!/usr/bin/env bash
# Stage a copy of the sample paper in the eval workspace (the current directory).
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
cp -R "$here/examples/sample-paper/." .
