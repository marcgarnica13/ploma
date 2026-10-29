---
paths:
  - "src/**/*.py"
  - "src/sports_pm/**/*.py"
  - "src/notebooks/**/*.py"
---

# Python Code Standards

**Standard:** Senior Principal Data Engineer + PhD researcher quality, for the **process-mining-on-soccer-event-data** pipeline (`src/sports_pm/`).

> **Scope:** Python 3.12 (uv-managed), no test suite. Code runs as **scripts / notebooks** (see `notebooks/discovery/`) and as the importable `sports_pm` package. Because there are no automated tests, **reproducibility and the documented invariants below are the safety net** — review and the [`python-reviewer`](../agents/python-reviewer.md) agent compensate for the missing test suite. The numerical discipline in §8 applies everywhere.

---

## 0. Run-from-`src/` convention

- The discovery scripts are run **from `src/`** so that `import sports_pm` and the env-var-derived
  paths resolve:
  ```bash
  cd src
  uv run python notebooks/discovery/parse_soccerlogs_matches.py
  uv run python notebooks/discovery/parse_statsbomb_matches.py
  ```
- Make `sports_pm` importable via `uv sync` (installs it editable from `pyproject.toml`); `export PYTHONPATH=src` also works.
- Do not write code that assumes a working directory other than `src/`.

## 1. Reproducibility

- **Pin dependencies** in `src/pyproject.toml` + `src/uv.lock` (pinned via uv: pm4py 2.7.22.4,
  pandas 3.0.3, numpy 2.4.6, plotly 5.24.1, kaleido 0.2.1, …). Any new dependency is added to
  `pyproject.toml` and locked with `uv lock` / `uv add`. (`src/requirements.txt` is a derived export
  kept in sync via `uv export`.)
- All paths relative to `src/` or routed through `RESULTS_FILE` via `viz/image_utils.save_image`; no
  hard-coded absolute paths and no hard-coded credentials.
- Any randomness (sampling, stochastic discovery, sweeps) is **seeded**, or the procedure is
  documented as deterministic.
- **MongoDB is a reproducibility caveat.** A fresh checkout cannot reproduce results without access to
  the `staging_soccerlogs` / `statsbomb_lake` databases. New code must fail **loudly** (a clear error)
  when Mongo is unreachable — never silently emit an empty DataFrame.

## 2. The env-var contract

Runtime reads these (some **at import time** — see §3):

| Var | Purpose |
|-----|---------|
| `MONGO_USER`, `MONGO_PWD`, `MONGO_STR` | Mongo SRV connection (`mongodb+srv://{USER}:{PWD}{STR}`) |
| `TAGS_FILE` | path to `src/sports_pm/parsers/tags2name.csv` (read at parser import) |
| `RESULTS_FILE` | output directory root for rendered figures |

- Do not add new required env vars without documenting them here and in `CLAUDE.md`.
- Read env vars with a clear failure message when unset; prefer reading them **inside functions**, not
  at import time (see §3).

## 3. Import-time side effect (TAGS_FILE) — load-bearing caveat

`src/sports_pm/parsers/soccerlogs.py` calls `os.environ['TAGS_FILE']` **at module import**. Therefore:

- `TAGS_FILE` **must be exported before** importing anything that transitively pulls in the parser, or
  the import raises.
- **Do not add new import-time `os.environ[...]` reads.** Defer env reads into functions where
  possible. If you must keep an import-time read, document it loudly at the top of the module.

## 4. The `action##zone` activity-key invariant

`create_event_log` builds pm4py activities as `"{action_id|sub_action_id}##{key_zone}"` with
case = `possession_count`. Downstream consumers (e.g. `HueristicField.get_overview`) **split node
names on `"##"`** to recover `(action_id, zone_id)`.

- Keep the `action##zone` format intact if you touch `create_event_log`.
- Any consumer must split on `"##"` and assume that field order; do not introduce a different
  delimiter or reorder the fields.

## 5. Coordinate-orientation caveat

Pitch orientation is **flipped** in several viz/zone places (`y -> FIELD_WIDTH - y`, attacking-direction
normalization in `SequenceEventField`). When touching pitch math:

- Verify orientation end-to-end — a mirrored pitch is a correctness bug, not a cosmetic one.
- Do zoning/`get_zone_id` on **standardized** 105x68 coordinates (`get_standard_positions` /
  `..._from_statsbomb`), never on raw coordinates.
- Avoid double-flips or mixing flipped and unflipped coordinates in the same computation.

## 6. Function design & style (PEP8)

- 4-space indent, no tabs; lines <= ~100 chars (see §7 for the math exception).
- `snake_case` functions/vars, `CapWords` classes, `UPPER_CASE` constants (`ZONES`, `FIELD_WIDTH`).
- **Explicit imports**, grouped stdlib / third-party / local. No `from x import *`.
- Verb-noun function names (`get_play_actions`, `create_event_log`, `get_standard_positions`).
- Docstrings on non-trivial functions (args, returns, **units** — metres on a 105x68 pitch).
- Type hints on public signatures **where practical** (Python 3.12 `typing` or builtin generics —
  pick one and be consistent); don't force hints on throwaway helpers.
- No magic numbers — the 24-zone grid, the dependency sweep range (0–0.99), pitch dimensions should be
  named/documented.
- Stable return contracts: `get_heuristic_net` returns
  `(heu_net, dependency, avg_fitness, generalization)` — callers depend on this order; do not change it
  without updating every caller.

## 7. Line Length & Mathematical Exceptions

**Standard:** keep lines <= 100 characters.

**Exception (math/coordinate formulas):** a line may exceed 100 chars **iff** breaking it harms
readability of the math (coordinate transforms, zone arithmetic, fitness computations) **and** an
inline comment explains the operation. Long lines in plain (non-math) code: minor penalty.

## 8. Numerical Discipline

See [`python-reviewer.md`](../agents/python-reviewer.md) Category 11 for the full checklist. Headline rules:

- **No float equality.** Never `==` on floats (coordinates, metrics). Use `math.isclose` /
  `np.isclose` with an explicit tolerance.
- **Pre-allocate, don't grow** in hot loops over events — use comprehensions or vectorized pandas, not
  repeated `list.append` in tight loops.
- **Explicit NaN policy.** Be explicit about `skipna` / dropped rows in pandas aggregations; document
  expected drops (e.g., possessions filtered out by the offensive filter).
- **Stable key dtypes.** Zone ids / match ids / `possession_count` keep a stable dtype — don't let a
  merge coerce an int id to float and break a later string-format of the case id.
- **`is None`, not `== None`; no mutable default arguments.**

## 9. Common Pitfalls

| Pitfall | Impact | Prevention |
|---------|--------|------------|
| Import before `TAGS_FILE` set | Import-time crash | Export `TAGS_FILE` first; defer env reads into functions |
| Changing the `##` activity-key format | Breaks `get_overview` and any net consumer | Keep `action##zone`; split on `"##"` |
| Zoning on raw coordinates | Wrong zone assignment | Standardize to 105x68 first |
| Mixed/forgotten coordinate flip | Mirrored pitch (silent correctness bug) | Verify orientation end-to-end |
| Silent empty result on Mongo failure | Fake "successful" empty run | Fail loudly when Mongo is unreachable |
| Hard-coded paths / credentials | Breaks on other machines; leaks secrets | Use env vars + `RESULTS_FILE` |
| Unpinned new dependency | Non-reproducible run | Add to `src/pyproject.toml` and re-lock with `uv lock` |

## 10. Code Quality Checklist

```
[ ] Runs from src/; sports_pm importable
[ ] New deps pinned in src/pyproject.toml + uv.lock (uv lock)
[ ] Env-var contract respected; no new import-time os.environ reads
[ ] TAGS_FILE exported before parser import
[ ] action##zone activity-key format preserved; consumers split on "##"
[ ] Coordinate orientation verified; zoning on standardized 105x68 coords
[ ] Explicit imports; PEP8 naming; docstrings + practical type hints
[ ] Randomness seeded or documented deterministic
[ ] Mongo failures surface a clear error (no silent empty results)
[ ] Numerical discipline: no float ==, stable key dtypes, explicit NaN policy
[ ] Comments explain WHY not WHAT
```
