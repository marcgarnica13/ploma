# ploma limits

Defaults below. Values under `limits:` and `pipeline.tolerances` in `ploma.yaml` override them; the resolved summary shows the active values.

| Loop or cap | Default |
|---|---|
| Review rounds (adversarial critic and fixer) | 5 |
| Critic and fixer iterations per finding | 5 |
| Verification retries after a failed check | 2 |
| CoVe regenerations of a failed section | 2 |
| DOI lookups per run | 50, 0.5 s apart |
| Review variance runs | N at most 5 |
| Revise-and-resubmit rounds | capped at r3 |
| Compile rebuilds to fix the first error | 2 |
| Deep audit loops | 5 |

Numeric tolerances when matching manuscript numbers to results:

| Kind | Tolerance |
|---|---|
| Counts | exact |
| Point metrics | 0.01 |
| Aggregates | 0.02 |
| Percentages | 0.1 percentage points |

When a cap is reached, stop, report what is still open and offer options. Never loop past a cap silently.
