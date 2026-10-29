# ploma

**Status: 0.1.0, unreleased.** Every lifecycle skill is installed. The design spec is in [`docs/superpowers/specs/`](docs/superpowers/specs/).

## What ploma is

ploma is a Claude Code plugin: a harness for writing, validating, reviewing and formatting LaTeX academic papers. A paper repo declares its facts once in `ploma.yaml` (manuscript path, build command, venue). Skills, agents, hooks and rules read that config instead of restating it. `/ploma:onboard` detects the facts by reading the repo and writes project files only after approval; `/ploma:doctor` says whether the repo is ready; a lifecycle of stages, each owned by one skill, is recommended from state that survives sessions. `/ploma:commit` refuses to commit until the required checks have passed.

## Install

The same commands work on both hosts (the development machine and the paper host). On a host without SSH keys for GitHub, set up HTTPS first, in the shell that starts Claude Code:

```
gh auth login && gh auth setup-git          # HTTPS credentials for git
export CLAUDE_CODE_PLUGIN_PREFER_HTTPS=1    # clone over HTTPS, skip the SSH probe
```

Then, inside Claude Code:

```
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

## Skills

- `/ploma:onboard`: detect the repo's facts, propose `ploma.yaml` and project files, write after approval.
- `/ploma:doctor`: read-only readiness check with a verdict.
- `/ploma:brainstorm`: 3 to 5 research questions with hypotheses, methods and pitfalls, fact-checked.
- `/ploma:lit-review`: literature search and synthesis; BibTeX offered only after a citation lookup.
- `/ploma:grill`: one question per turn with a recommended answer until no design decision is open.
- `/ploma:spec`: the binding paper spec (claims, evidence, venue constraints, page targets, decisions).
- `/ploma:write`: draft a section into a `_suggestion.tex` sibling; merges only on `--merge` and your yes.
- `/ploma:compile`: build the PDF, triage the log, check pages against the budget.
- `/ploma:format`: page map per section against the budget, a cut plan, pre-submission checks.
- `/ploma:validate-bib`: structural bibliography check; `--semantic` verifies entries against citation APIs.
- `/ploma:verify-claims`: fact-check claims with a fresh-context verifier (Chain-of-Verification).
- `/ploma:audit-reproducibility`: match reported numbers against the pipeline's results within tolerances.
- `/ploma:proofread`: report-only proofreading; fixes only after approval.
- `/ploma:review`: referee-style review; `--peer`, `--adversarial` and `--seven-pass` modes.
- `/ploma:devils-advocate`: 5 to 7 skeptical challenges to design choices; report only.
- `/ploma:respond`: point-by-point response to referee reports, locations fact-checked.
- `/ploma:commit`: commit behind the gate; asks before any push or pull request.
- `/ploma:status`: stage, gate, plan and session log on one screen.
- `/ploma:checkpoint`: structured snapshot of plan, decisions, pointers and next actions.
- `/ploma:compress-session`: distil the session into a note before auto-compaction.
- `/ploma:learn`: append a learning to the ledger; promote approved entries to a rule.
- `/ploma:deep-audit`: audit the ploma installation for drift and dangling references; fixes after approval.
- `/ploma:help`: what ploma is and which skill owns which stage.

Hooks (session context, pre-compact snapshot, context monitor, verify and log reminders) are silent in a repo without `ploma.yaml`. Venue profiles live in `venues/`, discipline profiles in `disciplines/`, both overridable per project in `ploma.d/`.

## Commit gate

`/ploma:commit` refuses to commit until the required checks have passed on the current files. It refreshes missing or stale `compile`, `bib` (structural) and `consistency` entries itself before it decides.

- Required: `compile` and `bib` (written by `/ploma:compile` and `/ploma:validate-bib`).
- Recommended: `consistency`, `claims`, `proofread`. `consistency` becomes required in 0.1.1.
- Override: write `commit anyway: <reason>` on its own line in your message. The reason is logged. After three consecutive overridden commits the gate stops accepting overrides until the required checks pass.

`python3 scripts/gate.py check` shows the gate state without committing.

## Running the tests

```
python3 -m pytest -q
claude plugin validate .
```

Tests need Python 3.10 or later and pytest. CI runs pytest on Python 3.10 and 3.12; `claude plugin validate .` runs locally, since the Claude CLI is not assumed in CI.

## Running the evals

Evals bill model calls. Run one case first and set a cost ceiling on any full run.

Each case under `evals/` stages a clean copy of `examples/sample-paper` with its `scaffold.sh`, so the runner needs `--scaffold`, and the skills call their scripts through Bash, so it needs `--allow-tools 'Bash(python3 *)'`. Smoke run, one case, one run, no baseline arm:

```
claude plugin eval . --trust-plugin --scaffold --allow-tools 'Bash(python3 *)' --case <case-name> --runs 1 --ablation none --keep-temp
```

Full run, with a cost ceiling:

```
claude plugin eval . --trust-plugin --scaffold --allow-tools 'Bash(python3 *)' --max-cost-usd 5
```

`<case-name>` is the `name` in a case's `case.yaml` (for example `doctor-sample-paper`). Results go to `evals/results/`, which is gitignored. Without a TeX installation the compile case expects a correctly reported FAIL.

On Ubuntu 23.10 or later the eval sandbox needs unprivileged user namespaces, which AppArmor restricts by default. Allow them with `sudo sysctl -w kernel.apparmor_restrict_unprivileged_userns=0` (add it to `/etc/sysctl.d/` to keep it across reboots). The sandbox's network proxy also needs `socat` (`sudo apt install socat`).

## Licence

Apache-2.0. See [`LICENSE`](LICENSE) and [`UPSTREAMS.md`](UPSTREAMS.md).
