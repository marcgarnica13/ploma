# transcripts

Real ploma runs on a scratch copy of `examples/demo-paper`. The film and the README stills take their words from these files.

## The rule

Film and still text may shorten these transcripts. They never add words to them.

## How they were made

`run_demo.sh` copies `examples/demo-paper` to `$HOME/ploma-demo-run`, makes it a git repository with one commit, and runs one headless Claude Code call per skill. Each call is:

```bash
claude -p --plugin-dir <repo> --permission-mode acceptEdits \
  --input-format stream-json --replay-user-messages \
  --output-format stream-json --verbose \
  --allowedTools "Bash(python3 *)" "Bash(git *)" "Bash(make *)" "Bash(mkdir *)" "Bash(ls *)" Read Write Edit Glob Grep
```

The prompt goes in on stdin as one stream-json user message. With `--replay-user-messages` the CLI writes that message back into the stream. So each raw file starts with the prompt as the CLI saw it.

The raw event stream goes to `raw/<name>.jsonl`. System events and rate limit events are dropped as the stream is written, because they list the local connectors, skills and plugins and the account's usage limits, which do not belong in a public repo. `render_transcript.py` turns it into `<name>.md`:

- `> <text>` for a user turn
- assistant text as written
- `[tool] <name> <first 80 chars of input>` for a tool call

Tool results and thinking blocks are left out of the markdown. They stay in the raw files. System events never reach the raw files, since they are dropped at capture.

All runs are from 2026-10-30, with Claude Code 2.1.314 and model `claude-opus-5-5`. No citation API keys were set, so the `validate-bib --semantic` lookups ran without a contact address, outside the polite pool.

## Files

| file | command | notes |
|---|---|---|
| `onboard.md` | `/ploma:onboard --yes` | |
| `compile-1.md` | `/ploma:compile` | first build |
| `validate-bib.md` | `/ploma:validate-bib --semantic` | |
| `write.md` | `/ploma:write intro` | writes `sections/intro_suggestion.tex` |
| `merge.md` | `/ploma:write intro --merge`, then `yes` | the `yes` is a second call with `-c`, appended to the same `merge.jsonl` |
| `compile-2.md` | `/ploma:compile` | build after the merge |
| `commit.md` | `/ploma:commit intro: ground the latency claim in bench.json --no-pr` | commit `5eb3f64` in the scratch copy |

`grill.md` and `spec.md` come from the owner's interactive session on the same scratch copy: `/ploma:grill sections/intro.tex`, then `/ploma:spec --no-verify`. Their raw source is `raw/session.jsonl`.

## Order of the runs

The headless runs came first: onboard, compile, validate-bib, write, merge, compile and commit. The owner's interactive grill and spec session ran afterwards on the same scratch copy. The original 31% intro was re-staged for that session. That is why `grill.md` says "staged edit".

## Things to know before quoting

- The allowlist has no `echo`, `cat` or compound shell rules. Some first tool calls were denied for that reason, and the skill retried with a plain `python3` call. Those denied calls still show as `[tool]` lines.
- No skill asked a question that needed an answer, apart from the merge `yes`.
- The merge and write runs report a warning that `results/bench.json` is missing. The file exists in the scratch copy. Treat that line as a ploma finding, not as a fact about the paper.
- The commit run says "I said 18 earlier". The 18 is in a thinking block, so it is not in `commit.md`. Do not quote that sentence.

## Fixed copy

The film's closing card is brand copy, not a ploma run. It is listed here so the film's traceability test treats it as sourced:

```
ploma
Your paper. Your claims. Checked.
```

## Rerun

```bash
bash media/transcripts/run_demo.sh            # fresh scratch copy, every step
bash media/transcripts/run_demo.sh compile-2  # reuse the scratch copy, one step
```

Each run bills model calls and overwrites the matching raw and markdown files.
