# ploma

**Status: milestone 1 (0.1.0-m1, unreleased).** Install, health, compile and bibliography checks work; writing, review and commit skills arrive in milestone 2. The design spec is in [`docs/superpowers/specs/`](docs/superpowers/specs/).

## What ploma is

ploma is a Claude Code plugin: a harness for writing, validating, reviewing and formatting LaTeX academic papers. A paper repo declares its facts once in `ploma.yaml` (manuscript path, build command, venue). Skills, agents, hooks and rules read that config instead of restating it. `/ploma:onboard` detects the facts by reading the repo and writes project files only after approval; `/ploma:doctor` says whether the repo is ready; a lifecycle of stages, each owned by one skill, is recommended from state that survives sessions. `/ploma:commit` refuses to commit until the required checks have passed.

## Install

The same commands work on both hosts (the development machine and the paper host). Inside Claude Code:

```
/plugin marketplace add marcgarnica13/ploma
/plugin install ploma@ploma
/ploma:onboard
```

On a host without SSH keys for GitHub, set up HTTPS first, in the shell that starts Claude Code:

```
gh auth login && gh auth setup-git          # HTTPS credentials for git
export CLAUDE_CODE_PLUGIN_PREFER_HTTPS=1    # clone over HTTPS, skip the SSH probe
```

Updates: `/plugin marketplace update ploma`, then `/reload-plugins`.

## What milestone 1 contains

- Skills: `/ploma:onboard`, `/ploma:doctor`, `/ploma:status`, `/ploma:help`, `/ploma:compile`, `/ploma:validate-bib`.
- Hooks: session context on start and after compaction, a pre-compact snapshot, a context monitor, a verify reminder after edits, a session log reminder on stop. Every hook is silent in a repo without `ploma.yaml`.
- Rules: eager core, style and limits rules; reference rules loaded on demand.
- Venue profiles (`venues/`) and discipline profiles (`disciplines/`), overridable per project in `ploma.d/`.
- Scripts behind the skills (`scripts/`), each with `--json` output, and eval cases for every installed skill (`evals/`).

Milestone 2 adds brainstorm, lit-review, grill, spec, write, format, verify-claims, audit-reproducibility, proofread, review, devils-advocate, respond, commit, checkpoint, compress-session, learn and deep-audit, plus the consistency and style checks and the agents behind them. Installed so far from milestone 2: audit-reproducibility, verify-claims, proofread, write, format.

## Commit gate

`/ploma:commit` (milestone 2) refuses to commit until the required checks have passed on the current files.

- Required: `compile` and `bib` (written by `/ploma:compile` and `/ploma:validate-bib`).
- Recommended: `consistency`, `claims`, `proofread`. `consistency` is recommended in 0.1.x and becomes required from 0.1.1.
- Override: reply `commit anyway: <reason>`. The reason is logged. After three consecutive overrides the gate stops accepting them until the required checks pass.

Until then, `python3 scripts/gate.py check` shows the gate state.

## Lifecycle

Milestone 1 installs onboard, doctor, status, help, compile and validate-bib; milestone 2 has added audit-reproducibility, verify-claims, proofread, write and format so far. Skills marked *planned* arrive in milestone 2; do not invoke them yet.

| # | Stage | Skill |
|---|---|---|
| 0 | Install | `/ploma:onboard` |
| 0b | Health | `/ploma:doctor` |
| 1 | Brainstorm | `/ploma:brainstorm` (planned) |
| 1b | Literature | `/ploma:lit-review` (planned) |
| 2 | Grill | `/ploma:grill` (planned) |
| 3 | Spec | `/ploma:spec` (planned) |
| 4 | Write | `/ploma:write <section>` |
| 5 | Compile | `/ploma:compile` |
| 5b | Format | `/ploma:format` |
| 6 | Validate | `/ploma:validate-bib`, `/ploma:verify-claims`, `/ploma:audit-reproducibility`, `/ploma:proofread` |
| 7 | Review | planned: `/ploma:review`, `/ploma:devils-advocate` |
| 8 | Respond | `/ploma:respond <report>` (planned) |
| 9 | Ship | `/ploma:commit` (planned) |
| any | Session | `/ploma:status`, `/ploma:help`; planned: `/ploma:checkpoint`, `/ploma:compress-session`, `/ploma:learn`, `/ploma:deep-audit` |

## Running the tests

```
python3 -m pytest -q
claude plugin validate .
```

Tests need Python 3.10 or later and pytest. CI runs pytest on Python 3.10 and 3.12; `claude plugin validate .` runs locally, since the Claude CLI is not assumed in CI.

## Running the evals

Each case under `evals/` stages a clean copy of `examples/sample-paper` with its `scaffold.sh`, so the runner needs `--scaffold`, and the skills call their scripts through Bash, so it needs `--allow-tools 'Bash(python3 *)'`. Smoke run, one case, one run, no baseline arm:

```
claude plugin eval . --trust-plugin --scaffold --allow-tools 'Bash(python3 *)' --case <case-name> --runs 1 --ablation none --keep-temp
```

Full run, with a cost ceiling:

```
claude plugin eval . --trust-plugin --scaffold --allow-tools 'Bash(python3 *)' --max-cost-usd 5
```

`<case-name>` is the `name` in a case's `case.yaml` (for example `doctor-sample-paper`). Results go to `evals/results/`, which is gitignored. Without a TeX installation the compile case expects a correctly reported FAIL.

## Licence

Apache-2.0. See [`LICENSE`](LICENSE) and [`UPSTREAMS.md`](UPSTREAMS.md).
