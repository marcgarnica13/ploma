#!/usr/bin/env bash
# Stage an onboarded git copy of the sample paper, then cite a key the bibliography lacks.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
src="$here/../../examples/sample-paper"
cp -R "$src/." .
rm -rf .ploma quality_reports build main.pdf main.log main.aux main.bbl main.blg
python3 "$here/../../scripts/project_files.py" --root . apply >/dev/null
git init -q .
git config user.email eval@example.org
git config user.name "ploma eval"
git add -- .
git commit -q -m "baseline"
# The working change the user wants to commit: a citation with no bibliography entry (bib FAIL, required).
printf '\nRelated ranking methods exist \\cite{missingkey2020}.\n' >> sections/intro.tex
