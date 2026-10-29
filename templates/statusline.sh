#!/usr/bin/env bash
# ploma status line: permission mode, model, git branch and the ploma lifecycle stage.
# Offered by /ploma:onboard. Copy to .claude/statusline.sh and set in .claude/settings.json:
#   "statusLine": {"type": "command", "command": "bash .claude/statusline.sh"}
# Claude Code pipes a JSON session snapshot on stdin. Reads only; never fails the session.

set -uo pipefail

INPUT="$(cat)"

parsed="$(printf '%s' "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
except Exception:
    d = {}
print(d.get('permission_mode', '?'))
print((d.get('model') or {}).get('display_name', '?'))
print((d.get('workspace') or {}).get('current_dir', '.'))
" 2>/dev/null || printf '?\n?\n\n')"

mode="$(printf '%s' "$parsed" | sed -n '1p')"
model="$(printf '%s' "$parsed" | sed -n '2p')"
cwd="$(printf '%s' "$parsed" | sed -n '3p')"
[ -n "$mode" ] || mode="?"
[ -n "$model" ] || model="?"
{ [ -n "$cwd" ] && [ "$cwd" != "." ]; } || cwd="$(pwd)"

case "$mode" in
    bypassPermissions) badge="[BYPASS]" ;;
    acceptEdits)       badge="[AUTO-EDIT]" ;;
    plan)              badge="[PLAN]" ;;
    default)           badge="[PROMPT]" ;;
    *)                 badge="[$mode]" ;;
esac

branch="$(git -C "$cwd" branch --show-current 2>/dev/null || true)"

stage=""
state_file="$cwd/{{ outputs.dir }}/ploma-state.yaml"
if [ -f "$state_file" ]; then
    stage="$(sed -n 's/^stage:[[:space:]]*//p' "$state_file" | head -n 1 | tr -d "\"'")"
fi
{ [ -n "$stage" ] && [ "$stage" != "null" ]; } || stage="none"

line="$badge  $model"
[ -n "$branch" ] && line="$line  @ $branch"
line="$line  ploma: $stage"

printf '%s' "$line"
