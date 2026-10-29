---
name: data-analysis
description: End-to-end Python data analysis on the process-mining pipeline — explore event/possession data → build the event log → discover/evaluate a process model → publication-ready tables and pitch figures. Use when user says "analyze this data", "explore these possessions", "run discovery on X", "full analysis workflow", or points at a dataset / Mongo source and asks for empirical results. Produces Python scripts under `src/` and outputs to `src/results/`.
argument-hint: "[dataset/source description or analysis goal]"
allowed-tools: ["Read", "Grep", "Glob", "Write", "Edit", "Bash", "Task", "Monitor"]
---

# Data Analysis Workflow

Run an end-to-end analysis in Python on the process-mining pipeline: load, explore, discover, evaluate, and produce publication-ready output.

**Input:** `$ARGUMENTS` — a data source (a Mongo database/collection, or a result dir) or a description of the analysis goal (e.g., "discover the offensive net for the StatsBomb sample at dependency 0.9 and report fitness").

---

## Constraints

- **Follow Python code conventions** in `.claude/rules/python-code-conventions.md`.
- **Run scripts from `src/`** so `sports_pm` and the env-var paths resolve; export `TAGS_FILE` before importing the parser.
- **Save scripts** under `src/` (or `src/notebooks/`) with descriptive names; **save outputs** to a timestamped dir under `src/results/` via `RESULTS_FILE` / `viz/image_utils.save_image`.
- **Preserve invariants:** the `action##zone` activity-key format, case id `possession_count`, coordinate orientation, zoning on standardized 105×68 coordinates.
- **Run the `python-reviewer` agent** on the generated script before presenting results.

---

## Workflow Phases

### Phase 0: Pre-Flight Report

**Before writing any analysis code, produce a Pre-Flight Report** showing you read the inputs. This prevents the failure mode where the agent hallucinates field names or skips project conventions.

Output block (in your response to the user, before Phase 1):

```markdown
## Pre-Flight Report

**Data source:** [Mongo db/collection or result dir]
- Event/possession fields found: [list]
- Match/possession counts: [count]
- Source schema: [Wyscout/soccerlogs or StatsBomb]

**Env contract:** [MONGO_*, TAGS_FILE, RESULTS_FILE present? TAGS_FILE exported before parser import?]

**Project conventions read:**
- `.claude/rules/python-code-conventions.md` — [one-line summary of most relevant rule]
- `.claude/rules/content-invariants.md` — [INV-9..INV-12 applicable]

**Task interpretation:** [one sentence restating what the user asked for]

**Plan:** [3-5 bullet outline of the pipeline run]
```

If any input cannot be read (missing env var, unreachable Mongo, missing file), stop and ask the user before proceeding.

### Phase 1: Setup and Data Loading

1. Module docstring with title, purpose, inputs, outputs, pipeline stage.
2. Explicit imports (stdlib / third-party / local); ensure `TAGS_FILE` is exported before importing the parser.
3. Set a seed (or document determinism) for any stochastic step.
4. Load match/event documents via the source layer (`logic/reducers.get_match_info`) and inspect.

### Phase 2: Exploratory Data Analysis

Generate diagnostic outputs:
- **Counts:** matches, possessions, possessions surviving `filter_offensive_sequences`.
- **Distributions:** possession length, actions per possession, zone occupancy.
- **Spatial patterns:** event heatmaps / scatter on the pitch (`MultipleEventField`), verifying orientation.
- **Sequence views:** a few possessions as connected paths (`SequenceEventField`).

Save diagnostic figures under the result dir via `save_image`.

### Phase 3: Main Analysis (discovery + evaluation)

Based on the goal:
- **Build the event log** with `create_event_log` (activity = `action##zone`, case = `possession_count`).
- **Discover** the model with `get_heuristic_net` (sweep the dependency threshold 0–0.99 to maximize token-replay fitness, or pass an explicit threshold).
- **Evaluate** conformance fitness on held-out matches where the claim is generalization — not only on the discovery data.
- **Compare** against at least one baseline; run targeted ablations (zone granularity, segmentation rule, threshold).

### Phase 4: Publication-Ready Output

**Tables:**
- Report metric values (avg fitness, generalization), the config (data source, dependency threshold), and N (matches / possessions).
- Export as `.tex`/`.csv`/`.json` for inclusion and quick viewing.

**Figures:**
- Render the discovered net over the pitch (`HueristicField`): zone bubbles + flow arrows over a heatmap.
- State pitch orientation and zone legend; verify the coordinate flip is correct.
- Export with explicit dimensions via `save_image` (PNG/SVG).

### Phase 5: Save and Review

1. Persist all key objects/metrics into the timestamped result dir.
2. Run the `python-reviewer` agent on the generated script:

```
Delegate to the python-reviewer agent:
"Review the script at src/notebooks/discovery/[script_name].py"
```

3. Address any Critical or High issues from the review (especially the four documented gotchas).

---

## Script Structure

Follow this template:

```python
"""
[Descriptive Title]
Purpose: [what this script does]
Inputs:  [Mongo source / result dir]
Outputs: [figures, tables, metrics under src/results/<run>/]
Pipeline stage: Source -> Segment -> Filter -> Standardize -> Discover -> Visualize
"""
import os
# TAGS_FILE must be set before importing the parser (import-time env read)
assert "TAGS_FILE" in os.environ, "export TAGS_FILE before running (see CLAUDE.md)"

import json
import pandas as pd
import pm4py

from sports_pm.logic.reducers import get_match_info
from sports_pm.logic.filters import filter_offensive_sequences_statsbomb
from sports_pm.logic.discovery import create_event_log, get_heuristic_net
from sports_pm.viz.image_utils import save_image

# 1. Data loading ----
# 2. Exploratory analysis ----
# 3. Discovery + evaluation ----
# 4. Tables and pitch figures ----
# 5. Export (metrics + figures to src/results/<run>/) ----
```

---

## Important

- **Reproduce, don't guess.** If the user specifies a config, run exactly that.
- **Show your work.** Print/inspect counts and distributions before discovery.
- **Check for issues.** Empty filter output, mirrored pitch orientation, dtype drift on keys, silent empty results on Mongo failure.
- **No hardcoded paths/credentials.** Use the env-var contract; run from `src/`.

## Long-running fits: use the Monitor tool (Apr 2026)

For discovery sweeps or large batch runs that take more than a couple of minutes, launch via Bash with `run_in_background: true` and then use Anthropic's **Monitor tool** to stream stdout into the conversation in real time. Pattern:

1. Background-launch: `python notebooks/discovery/parse_statsbomb_matches.py` (from `src/`) with `run_in_background: true`. Capture the `bash_id`.
2. Use Monitor on the `bash_id` until a milestone fires (e.g., `metrics written`, or process exit).
3. Continue or course-correct based on what the stream reveals.

This avoids the polling-loop anti-pattern (`sleep 30; check; sleep 30; check`) and avoids burning cache on idle waits.
