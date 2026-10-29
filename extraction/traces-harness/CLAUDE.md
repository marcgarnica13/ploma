# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A research codebase applying **process mining** to soccer event data: raw match events are
turned into possession "traces", a process model (heuristic net / Petri net) of offensive play
is discovered with `pm4py`, scored by conformance fitness, and rendered onto a pitch. This repo
holds both the **analysis code** (`src/`) and the **paper** (`manuscript/`) describing it.

## Repository layout

| Path                 | What it is | How to operate it |
|----------------------|------------|-------------------|
| `src/`               | The Python project (process-mining pipeline + pitch visualizations). Python 3.12 (uv-managed), no test suite. | See **Setup & running** and **Pipeline architecture** below. |
| `manuscript/`        | The LaTeX source of the paper, currently targeting a **Machine Learning journal** (Springer LLNCS class). Self-contained: `samplepaper.tex` + `mybib.bib` + `fig1–5.pdf` + class/style files. | `cd manuscript && make` → `samplepaper.pdf`. See **Building the manuscript**. |
| `review/`            | Peer-review reports (`review1–3.md`) from the paper's **previous** submission (a conference/ADS track). These are the comments the journal resubmission should address. | Read-only reference; not part of any build. |

A `previous_manuscript/` folder used to hold the older submission's LaTeX; its content was merged
into `manuscript/` and the folder removed. If you see references to it, they are stale.

Python 3.12, managed with **uv**. No build system for the code, no test suite — `src/` runs as scripts/notebooks. The source of truth for dependencies is `src/pyproject.toml` + `src/uv.lock` (`src/requirements.txt` is a derived export kept for tooling that expects it).

## Setup & running

```bash
cd src
uv sync                                  # pm4py 2.7.22.4, pandas 3.0.3, numpy 2.4.6, plotly 5.24.1, kaleido 0.2.1
                                         # (creates the venv from pyproject.toml + uv.lock; `sports_pm` is installed editable)
```

The analysis is driven by two scripts, **run from `src/`** (via `uv run`) so `sports_pm` and the env-var paths resolve:

```bash
uv run python notebooks/discovery/parse_soccerlogs_matches.py    # Wyscout/Soccerlogs source
uv run python notebooks/discovery/parse_statsbomb_matches.py     # StatsBomb source
```

Required environment variables (read at runtime, some **at import time** — see gotchas):

- `MONGO_USER`, `MONGO_PWD`, `MONGO_STR` — Mongo SRV connection parts (`mongodb+srv://{USER}:{PWD}{STR}`)
- `STATSBOMB_DATA_DIR` — path to a local StatsBomb open-data JSON tree (`matches`/`lineups`/`events`); used by the StatsBomb-JSON loader as an alternative to the Mongo source (default: `/home/marc/Documents/statsbomb_data/data`)
- `TAGS_FILE` — path to `src/sports_pm/parsers/tags2name.csv`
- `RESULTS_FILE` — output directory root for rendered figures (`viz/image_utils.save_image`)

Loading raw StatsBomb JSON into Mongo is a separate `click` CLI:

```bash
python sports_pm/scripts/stats_bomb.py upload-to-mongo <data_folder>
```

## Pipeline architecture

The data flow is linear; each stage lives in its own module under `src/sports_pm/`:

1. **Source** — match/event documents pulled from MongoDB (`staging_soccerlogs` or `statsbomb_lake`
   databases), or — for StatsBomb — read directly from a local StatsBomb open-data JSON tree via the
   JSON loader (`STATSBOMB_DATA_DIR`), so Mongo is no longer the only source.
   `logic/reducers.get_match_info` normalizes match metadata across the schemas.
2. **Segment into plays** — `parsers/soccerlogs.py` splits a match's event stream into play actions.
   `get_play_actions` (Wyscout) breaks possessions on interruptions/fouls/offside/ball-loss/shots;
   `get_play_actions_statsbomb` groups by StatsBomb's native `possession` id.
3. **Filter to offensive sequences** — `logic/filters.py` keeps only possessions that start in the
   own half and end inside the opponent box (`filter_offensive_sequences[_statsbomb]`). It stamps
   each kept possession with `possession_count = "{match_id}_{team_id}_{seq_index}"` (this becomes
   the process-mining **case id**).
4. **Standardize space** — `configuration/standard.py` converts raw coordinates to a 105×68 m pitch
   (`get_standard_positions` from %, `..._from_statsbomb` from 120×80) and assigns each point one of
   **24 zones** (`ZONES`, a 6-height × 4-rail grid) via `get_zone_id`.
5. **Discover & evaluate** — `logic/discovery.py`. `create_event_log` builds the pm4py event log
   where **activity = `"{action_id|sub_action_id}##{key_zone}"`** and case = `possession_count`.
   `get_heuristic_net` discovers a heuristic net; given no `dependency` threshold it sweeps 0–0.99 to
   maximize token-replay fitness. Returns `(heu_net, dependency, avg_fitness, generalization)`.
6. **Visualize** — `viz/`. `field_graph.py` is the core: `FieldGraph` base + `MultipleEventField`
   (scatter/heatmap of events), `SequenceEventField` (single possession as a connected path), and
   `HueristicField` (renders a discovered heuristic net as zone bubbles + flow arrows over a pitch
   heatmap). `field_functions.py` and `image_utils.save_image` wrap plotting and PNG/SVG export.

`src/sports_pm/src/overview.py` is a standalone helper that summarizes available StatsBomb open-data
matches via `floodlight`.

## Building the manuscript

The paper is independent of the Python code — it only needs a LaTeX toolchain (TeX Live).

```bash
cd manuscript
make            # or `make build`: pdflatex -> bibtex -> pdflatex x2  ->  samplepaper.pdf
make clean      # remove LaTeX aux files, keep the PDF
make cleanall   # also remove samplepaper.pdf
```

The four-step build (3× `pdflatex` around one `bibtex`) is required to resolve citations and
cross-references. No GitHub remote is needed; the folder is self-contained and also compiles as-is
on Overleaf (set `samplepaper.tex` as the main document). Authors are intentionally **anonymized**
in `samplepaper.tex` (real author block is commented out) — restore it before a non-blind submission.

## Conventions & gotchas

- **Import-time side effect:** `parsers/soccerlogs.py` reads `os.environ['TAGS_FILE']` at module
  import. `TAGS_FILE` must be set *before* importing anything that pulls in the parser, or import fails.
- **Activity key coupling:** anything consuming a discovered net splits node names on `"##"` to recover
  `(action_id, zone_id)` (e.g. `HueristicField.get_overview`). Keep the `action##zone` format intact if
  you change `create_event_log`.
- **Coordinate orientation** is flipped in several places (`y -> FIELD_WIDTH - y`, attacking-direction
  normalization in `SequenceEventField`). Verify pitch orientation when touching viz math.
- **Outputs are timestamped result dirs**, not committed code: `src/results/offensive_statsbomb_pass_09x/`
  etc. encode the dependency-threshold / event-type variants of past runs.
- `scripts/{nba,rugby,soccerlogs}_data.py` are source-specific loaders; only the soccerlogs/statsbomb
  paths are wired into the discovery pipeline.

## Claude Code harness (`.claude/`)

This repo ships a committed, academic-tuned Claude Code harness so collaborators get the same
agent setup. **The whole tree (`src/`, `manuscript/`, `review/`) is now a single git repo at the
root** — the old nested `src/.git` (remote `marcgarnica13/sports-pm`, branch `feature/import_data`)
was retired; its full history is archived on that GitHub remote and in `src-history-backup.bundle`
(git-ignored).

**Two layers:**

1. **superpowers** — install once as a plugin (methodology: brainstorm → plan → TDD → subagent
   review → git worktrees → systematic debugging). No API key.
   ```
   /plugin marketplace add obra/superpowers-marketplace
   /plugin install superpowers@superpowers-marketplace
   ```
2. **Vendored academic layer** in `.claude/` — committed, adapted to this project (process mining /
   ML / LLNCS). Key slash-skills:

   | Skill | What it does here |
   |-------|-------------------|
   | `/compile-latex` | Builds `manuscript/samplepaper.tex` via `cd manuscript && make` (pdflatex, **not** xelatex); reports overfull boxes + undefined citations. |
   | `/review-paper [--peer ML] [--adversarial]` | Manuscript review; `--peer ML` runs a simulated Springer **Machine Learning** journal pipeline (editor + 2 dispositioned referees). |
   | `/respond-to-referees` | Drafts a point-by-point response from `review/review1–3.md` against the revised manuscript (CoVe-verified). |
   | `/validate-bib [--semantic]` | Checks `\cite` keys vs `manuscript/mybib.bib`; DOI verification via Crossref / Semantic Scholar / OpenAlex (**all free, no API key**). |
   | `/audit-reproducibility` | Cross-checks numeric claims in the paper against the Python pipeline outputs + env-var / `pyproject.toml`+`uv.lock` contract. |
   | `/proofread`, `/verify-claims`, `/seven-pass-review`, `/deep-audit`, `/devils-advocate` | Writing, fact-checking, and adversarial review passes. |
   | `/lit-review`, `/research-ideation`, `/interview-me`, `/data-analysis` | Literature, ideation, idea-formalization, and the Python analysis workflow. |

   Supporting `agents/` (incl. `python-reviewer` aware of the gotchas above), `rules/`,
   `references/journal-profiles.md` (the ML profile), and audited `hooks/` round it out.
   `settings.json` uses conservative permissions (no `bypassPermissions`; secrets `**/.env*` denied).
   Per-user overrides go in the git-ignored `.claude/settings.local.json`.
