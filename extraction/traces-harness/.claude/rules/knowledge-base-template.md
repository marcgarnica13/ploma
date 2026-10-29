---
paths:
  - "manuscript/**/*.tex"
  - "src/**/*.py"
---

# Project Knowledge Base: Process Mining for Soccer Possession Traces

<!-- Fill in the tables below with project-specific content.
     Claude reads this before creating/modifying paper or pipeline content. -->

## Notation / Terminology Registry

| Term | Convention | Example | Anti-Pattern |
|------|-----------|---------|-------------|
| possession trace | a case in the event log | case id = `possession_count` | calling it a "sequence" loosely |
| zone | one of 24 (6×4) standardized cells | `get_zone_id` on 105×68 coords | zoning on raw coordinates |
| activity | `"{action_id\|sub_action_id}##{key_zone}"` | split on `##` to recover (action, zone) | changing the `##` delimiter |

## Symbol / Field Reference

| Symbol/Field | Meaning | Introduced |
|--------------|---------|------------|
| `possession_count` | case id `{match_id}_{team_id}_{seq_index}` | offensive filter |
| `avg_fitness` | token-replay conformance fitness | discovery/eval |
| `dependency` | heuristic-net dependency threshold | discovery |

## Pipeline Progression

| # | Stage | Core Question | Key Module |
|---|-------|--------------|------------|
| 1 | Source | which matches/events? | `logic/reducers.get_match_info` |
| 2 | Segment | where does a possession end? | `parsers/soccerlogs.py` |
| 3 | Filter | which possessions are offensive? | `logic/filters.py` |
| 4 | Standardize | which zone? | `configuration/standard.py` |
| 5 | Discover/Eval | which model, how good? | `logic/discovery.py` |
| 6 | Visualize | what does it look like on the pitch? | `viz/field_graph.py` |

## Empirical Applications / Datasets

| Source | Schema | Database | Purpose |
|--------|--------|----------|---------|
| Wyscout / Soccerlogs | % coordinates | `staging_soccerlogs` | one data provider |
| StatsBomb | 120×80 coordinates | `statsbomb_lake` | second data provider |

## Design Principles

| Principle | Rationale | Where Applied |
|-----------|-----------|---------------|
| evaluate on held-out data | generalization claims need out-of-sample evidence | discovery/eval |
| standardize before zoning | comparable space across providers | `standard.py` |

## Anti-Patterns (Don't Do This)

| Anti-Pattern | What Happened | Correction |
|-------------|---------------|-----------|
| import parser before TAGS_FILE set | import-time crash | export `TAGS_FILE` first |
| zoning on raw coords | wrong zone ids | standardize to 105×68 first |
| fit-on-train fitness as generalization | overstated result | use held-out matches |

## Python Code Pitfalls

| Bug | Impact | Fix |
|-----|--------|-----|
| mixed/forgotten coordinate flip | mirrored pitch | verify orientation end-to-end |
| silent empty result on Mongo failure | fake successful run | fail loudly |
| changing `##` activity-key format | breaks net consumers | keep `action##zone` |

<!-- Add as needed: Metric Registry, Run Configs, Tolerance Thresholds -->
