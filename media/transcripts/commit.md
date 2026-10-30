> /ploma:commit intro: ground the latency claim in bench.json --no-pr

[tool] Bash ls ploma.yaml && git status --porcelain && grep -E "fix-and-recheck|Consecutive

[tool] Read /home/mgarnica/papers/rules/eager/limits.md

[tool] Bash ls ploma.yaml && git status --porcelain

Caps (from limits.md, no `limits:` override for these in ploma.yaml summary): fix-and-recheck rounds 2, consecutive overrides 3. Running the gate.

[tool] Bash python3 "/home/mgarnica/papers/scripts/commit_gate.py" prepare --json; echo "EXI

[tool] Bash python3 "/home/mgarnica/papers/scripts/commit_gate.py" prepare --json

[tool] Bash python3 "/home/mgarnica/papers/scripts/doctor.py" .

[tool] Bash git rev-parse --abbrev-ref HEAD && git status --porcelain -uall && git diff --st

[tool] Bash git add -- .gitignore ploma.yaml sections/intro.tex .claude/rules/ploma-manuscri

[tool] Bash git commit -F - <<'PLOMA_COMMIT' intro: ground the latency claim in bench.json C

I committed your changes as **`5eb3f64` intro: ground the latency claim in bench.json** on `master`. The working tree is clean.

- **Paths:** 16 files went into the commit. I said 18 earlier, but the list had 16. The commit includes the onboarding files, the refreshed reports under `quality_reports/` and the state event.
- **Gate:** it passed. compile, bib and consistency all passed and are up to date. No override was used.
- **Push and pull request:** skipped because you passed `--no-pr`.
- **Checks still recommended:** neither has been run yet: `/ploma:verify-claims` (claims) and `/ploma:proofread`.
- **Doctor warning:** `reviews.glob` in ploma.yaml points to a directory that doesn't exist. This doesn't block anything; create the directory when referee reports arrive, or correct the path.
