# ploma

**Status: under construction (0.1.0, unreleased).** The plugin skeleton is in place; the lifecycle skills are being built. Start with [`BRIEF.md`](BRIEF.md) and the design spec in [`docs/superpowers/specs/`](docs/superpowers/specs/).

## What ploma is

ploma is a Claude Code plugin: a harness for writing, validating, reviewing and formatting LaTeX academic papers. A paper repo declares its facts once in `ploma.yaml` (manuscript path, build command, venue). Skills, agents, hooks and rules read that config instead of restating it. `/ploma:onboard` detects the facts by reading the repo and writes project files only after approval; `/ploma:doctor` says whether the repo is ready; a lifecycle of stages, each owned by one skill, is recommended from state that survives sessions. `/ploma:commit` refuses to commit until the required checks have passed.

## Install

```
gh auth login && gh auth setup-git          # HTTPS credentials
export CLAUDE_CODE_PLUGIN_PREFER_HTTPS=1    # skip the SSH probe (needed on Marc's paper host)
/plugin marketplace add marcgarnica13/ploma
/plugin install ploma@ploma
/ploma:onboard
```

Updates: `/plugin marketplace update ploma`, then `/reload-plugins`.

## Lifecycle

| # | Stage | Skill |
|---|---|---|
| 0 | Install | `/ploma:onboard` |
| 0b | Health | `/ploma:doctor` |
| 1 | Brainstorm | `/ploma:brainstorm` |
| 1b | Literature | `/ploma:lit-review` |
| 2 | Grill | `/ploma:grill` |
| 3 | Spec | `/ploma:spec` |
| 4 | Write | `/ploma:write <section>` |
| 5 | Compile | `/ploma:compile` |
| 5b | Format | `/ploma:format` |
| 6 | Validate | `/ploma:validate-bib`, `/ploma:verify-claims`, `/ploma:audit-reproducibility`, `/ploma:proofread` |
| 7 | Review | `/ploma:review`, `/ploma:devils-advocate` |
| 8 | Respond | `/ploma:respond <report>` |
| 9 | Ship | `/ploma:commit` |
| any | Session | `/ploma:status`, `/ploma:checkpoint`, `/ploma:compress-session`, `/ploma:learn`, `/ploma:deep-audit`, `/ploma:help` |

## Running the tests

```
python3 -m pytest -q
claude plugin validate .
```

Tests need Python 3.10 or later and pytest. CI runs pytest on Python 3.10 and 3.12; `claude plugin validate .` runs locally, since the Claude CLI is not assumed in CI.

## Licence

Apache-2.0. See [`LICENSE`](LICENSE) and [`UPSTREAMS.md`](UPSTREAMS.md).
