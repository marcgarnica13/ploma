> /ploma:spec --no-verify

[tool] Bash cat /home/mgarnica/papers/skills/spec/references/paper-spec-template.md; echo --

[tool] Write /home/mgarnica/ploma-demo-run/quality_reports/paper_spec.md

[tool] AskUserQuestion [{"header": "Sample", "question": "results.tex:4 says \"three agent frameworks\"

[tool] Bash cd /home/mgarnica/ploma-demo-run/quality_reports && python3 - <<'EOF' p='paper_s

[tool] AskUserQuestion [{"header": "Fairness", "question": "Hawser samples whole traces to bound storag

[tool] Bash python3 - <<'EOF' p='paper_spec.md' s=open(p).read() s=s.replace("Comparison fai

[tool] Bash python3 - <<'EOF' p='paper_spec.md' L=open(p).read().split('\n') i=[k for k,l in

[tool] AskUserQuestion [{"header": "Sections", "question": "The manuscript has only Introduction, Metho

[tool] Bash python3 - <<'EOF' p='paper_spec.md' s=open(p).read() old=s[s.index("| Introducti

[tool] Bash sed -n 56,100p /home/mgarnica/ploma-demo-run/quality_reports/paper_spec.md

[tool] Bash cd /home/mgarnica/ploma-demo-run/quality_reports && sed -i 's/the number and kin

The spec is written at `quality_reports/paper_spec.md`. It's recorded as WARN because you skipped the citation check with `--no-verify`, and 8 questions are still open.

**Identity:** Hawser is a tracer for LLM agents that records the causal link from each model decision to the tool results it consumed. On 1200 tasks across three agent frameworks it cuts median trace-query latency by 27.4% against an OpenTelemetry pipeline, at 1.1 times the storage. It is for operators who debug failed agent runs.

**Claims**

| ID | Claim | Evidence | Status |
|---|---|---|---|
| C1 | Each decision is linked to the tool results it read, so a task's trace is a graph (DAG), not a tree of spans | `sections/method.tex:5-9` | supported (design) |
| C2 | The query planner walks indexed edges backwards instead of scanning whole traces | `sections/method.tex:12-16` | supported (design), no separate measurement |
| C3 | 27.4% median latency cut vs OpenTelemetry | `bench.json:latency_cut_vs_otel_pct` | supported |
| C4 | 41.2% median latency cut vs raw logs | `bench.json:latency_cut_vs_rawlogs_pct` | supported |
| C5 | Storage is 1.1 times the OpenTelemetry pipeline's | `bench.json:storage_ratio` | supported |
| C6 | 1200 tasks across 3 frameworks | `bench.json:n_tasks`, `n_frameworks` | supported |
| C7 | 95% bootstrap confidence interval on each latency cut | planned: new results keys | planned |

**Sections:** six sections totalling 9.5 of 10 pages, references excluded:

| Section | Pages |
|---|---|
| Introduction | 1.5 |
| Related work (new file) | 1.5 |
| Method | 2.5 |
| Evaluation setup (new file) | 1.5 |
| Results | 1.5 |
| Limitations and conclusion (new file) | 1.0 |

**Locked decisions:** 11. Four came from the intro decision log (L1–L4) and one from the discipline card (L5, empirical study). Six came from this interview:
- **L6:** Evaluation setup names the three frameworks, where the tasks come from, and the query set.
- **L7:** report a 95% bootstrap confidence interval on each latency cut.
- **L8:** time every back end on the same unsampled traces.
- **L9:** run /ploma:lit-review before writing related work.
- **L10:** the six-section layout above.
- **L11:** two figures, F1 (span tree vs Hawser's graph) and F2 (latency distribution per back end).

There are no other decision logs.

**Open questions**
- **Q1:** your staged intro still says "31%" with no baseline. Redraft it to 27.4% vs OpenTelemetry before committing.
- **Q2:** `pipeline.rerun` is not set in `ploma.yaml`.
- **Q3:** I need the framework names, where the tasks come from, and the query set. Only you have these.
- **Q4:** the confidence-interval keys don't exist in `bench.json` yet.
- **Q5:** check whether the current `bench.json` numbers were measured on unsampled, identical traces. If not, C3–C5 need a rerun.
- **Q6:** the comparison to existing agent-tracing tools is empty until the lit review runs.
- **Q7:** F2 has no plotting script yet.
- **Q8:** the code availability statement needs a URL.

**Citation check:** skipped because of `--no-verify`.

Run /ploma:write <section> --from-spec to draft against this spec.
