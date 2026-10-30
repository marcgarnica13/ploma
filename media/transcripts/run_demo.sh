#!/usr/bin/env bash
# Run ploma for real on a scratch copy of examples/demo-paper and keep the transcripts.
#
# Usage: bash media/transcripts/run_demo.sh [step ...]
# With no steps it rebuilds the scratch copy and runs every step in order.
# With steps it reuses the scratch copy and runs only those steps.
# Steps: onboard compile-1 validate-bib write merge compile-2 commit
#
# Each step is one headless Claude Code call. The prompt goes in as a
# stream-json user message with --replay-user-messages, so the raw JSONL
# records the prompt as the CLI saw it. System and rate limit events are
# dropped as the stream is written, so no local setup reaches the repo.
set -euo pipefail

PLUGIN=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
RUN=$HOME/ploma-demo-run
RAW=$PLUGIN/media/transcripts/raw
OUT=$PLUGIN/media/transcripts
RENDER=$OUT/render_transcript.py

ALLOWED=("Bash(python3 *)" "Bash(git *)" "Bash(make *)" "Bash(mkdir *)" "Bash(ls *)"
         Read Write Edit Glob Grep)

mkdir -p "$RAW"

setup() {
  # Deletes the scratch copy at $HOME/ploma-demo-run.
  rm -rf "$RUN"
  cp -r "$PLUGIN/examples/demo-paper" "$RUN"
  (cd "$RUN" && git init -q && git add -A && git commit -qm "demo paper")
  echo "scratch copy: $RUN"
}

warn_keys() {
  local name
  for name in OPENALEX_API_KEY SEMANTIC_SCHOLAR_API_KEY CROSSREF_MAILTO; do
    if [ -z "${!name:-}" ]; then
      echo "warning: $name is unset; citation lookups run without a contact address, outside the polite pool" >&2
    fi
  done
}

# One user message as a stream-json line.
user_line() {
  python3 -c 'import json, sys; print(json.dumps({"type": "user", "message": {"role": "user", "content": sys.argv[1]}}))' "$1"
}

# claude_call <jsonl> <prompt> [-c]
claude_call() {
  local jsonl=$1 prompt=$2 cont=${3:-}
  local args=(-p)
  if [ -n "$cont" ]; then args+=(-c); fi
  args+=(--plugin-dir "$PLUGIN"
         --permission-mode acceptEdits
         --input-format stream-json --replay-user-messages
         --output-format stream-json --verbose
         --allowedTools "${ALLOWED[@]}")
  local start=$SECONDS status=0
  # Setup events are dropped at capture: they list local connectors, skills, plugins and account limits.
  user_line "$prompt" | (cd "$RUN" && claude "${args[@]}") \
    | python3 "$RENDER" --strip-system >> "$jsonl" || status=$?
  echo "step $(basename "$jsonl" .jsonl): exit $status, $((SECONDS - start))s" >&2
  python3 - "$jsonl" <<'PY' >&2
import json, sys
last = None
for line in open(sys.argv[1], encoding="utf-8"):
    try:
        event = json.loads(line)
    except json.JSONDecodeError:
        continue
    if event.get("type") == "result":
        last = event
if last:
    print(f"  result: {last.get('subtype')}, is_error={last.get('is_error')}, turns={last.get('num_turns')}")
    for denial in last.get("permission_denials") or []:
        print(f"  denied: {denial.get('tool_name')} {json.dumps(denial.get('tool_input'))[:120]}")
PY
  return "$status"
}

# step <name> <prompt>
step() {
  local name=$1 prompt=$2
  : > "$RAW/$name.jsonl"
  claude_call "$RAW/$name.jsonl" "$prompt"
  if [ "$name" = merge ]; then
    claude_call "$RAW/$name.jsonl" "yes" -c
  fi
  python3 "$RENDER" "$RAW/$name.jsonl" "$OUT/$name.md"
}

prompt_for() {
  case $1 in
    onboard) echo "/ploma:onboard --yes" ;;
    compile-1|compile-2) echo "/ploma:compile" ;;
    validate-bib) echo "/ploma:validate-bib --semantic" ;;
    write) echo "/ploma:write intro" ;;
    merge) echo "/ploma:write intro --merge" ;;
    commit) echo "/ploma:commit intro: ground the latency claim in bench.json --no-pr" ;;
    *) echo "unknown step: $1" >&2; return 1 ;;
  esac
}

STEPS=(onboard compile-1 validate-bib write merge compile-2 commit)
if [ $# -eq 0 ]; then
  setup
  set -- "${STEPS[@]}"
fi
warn_keys
for name in "$@"; do
  prompt=$(prompt_for "$name") || exit 1
  step "$name" "$prompt"
done

echo "scratch copy left in place: $RUN"
