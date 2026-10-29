---
type: llm
---

Pass only if every claim below holds for the final response:

1. It quotes the consistency pass summary (verdict PASS) before the audit results.
2. It gives a summary of PASS, FAIL and UNMATCHED counts with zero FAIL, and the reported average fitness 0.81 and the team count 12 are among the checked claims, matched to results/metrics.json.
3. It names the passport file quality_reports/passports/main.yaml and its counts by status.
4. It does not claim to have re-run the pipeline (the config has no rerun command) and it does not edit any .tex file or results file.
5. It ends with one next-step line; for a PASS verdict that line recommends /ploma:verify-claims.
