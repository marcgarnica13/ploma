# Testing

How to run ploma's test suite, how the maintainers field-test it, and the optional evals.

## Running the tests

```
python3 -m pytest -q
claude plugin validate .
```

Tests need Python 3.10 or later and pytest. CI runs pytest on Python 3.10 and 3.12; `claude plugin validate .` runs locally, since the Claude CLI is not assumed in CI.

## Field tests

The maintainers test ploma with the pytest suite above plus headless field tests on real paper repos, without billed eval runs. On Claude Code:

```
cd <paper-repo>
claude -p --plugin-dir /path/to/ploma "/ploma:doctor"
```

On Codex, use an isolated home, a local marketplace add and a headless run:

```
export CODEX_HOME=/tmp/ploma-codex-home        # keep the real ~/.codex untouched; copy auth.json into it
codex plugin marketplace add /path/to/ploma && codex plugin add ploma@ploma
cd <paper-repo>
codex exec --skip-git-repo-check --dangerously-bypass-hook-trust -s workspace-write '$ploma:doctor'
```

`--dangerously-bypass-hook-trust` is needed because a headless run cannot trust hooks interactively.

Swap in any skill. A field test passes when the skill's report and verdict match what a careful author would conclude about that repo.

## Evals

`evals/` holds one `claude plugin eval` case per skill, staged on `examples/sample-paper`. They bill model calls and are not part of the release process. If you run them, use `--scaffold --allow-tools 'Bash(python3 *)'`, one case at a time (`--case <name> --runs 1 --ablation none`), and a `--max-cost-usd` ceiling. On Ubuntu 23.10 or later the eval sandbox needs `kernel.apparmor_restrict_unprivileged_userns=0` and `socat`.
