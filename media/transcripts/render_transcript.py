"""Render a Claude Code JSONL transcript as plain markdown.

Two input shapes are accepted. The first is the event stream from
`claude -p --output-format stream-json --verbose`. The second is a session
file under ~/.claude/projects/. Both wrap each turn in a `message` envelope.
Extra fields are ignored.

Output format:
  > <user text>                          for each user turn
  <assistant text>                       verbatim
  [tool] <name> <first 80 chars of input> for each tool call

Tool results, system events and result events are left out.

Usage:
  python3 render_transcript.py <in.jsonl> <out.md>
  python3 render_transcript.py --strip-system [<file.jsonl> ...]

--strip-system drops events that describe the local setup rather than the
conversation: `system` events (init, hooks) and `rate_limit_event` events.
The init event lists the owner's connectors, skills and plugins, and the rate
limit event describes the account. With files it rewrites them in place.
With no files it filters stdin to stdout.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

TOOL_INPUT_CHARS = 80
_COMMAND_RE = re.compile(r"<command-name>(.*?)</command-name>", re.S)
_ARGS_RE = re.compile(r"<command-args>(.*?)</command-args>", re.S)


def _tool_summary(name: str, tool_input) -> str:
    """One line for a tool call: its name and the start of its input."""
    if isinstance(tool_input, dict):
        if len(tool_input) == 1:
            value = next(iter(tool_input.values()))
        else:
            for key in ("command", "file_path", "pattern", "skill", "prompt", "url", "query"):
                if key in tool_input:
                    value = tool_input[key]
                    break
            else:
                value = json.dumps(tool_input, ensure_ascii=False)
    else:
        value = tool_input
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    text = " ".join(text.split())[:TOOL_INPUT_CHARS]
    return f"[tool] {name} {text}".rstrip()


def _user_text(text: str) -> str | None:
    """The text a person typed, or None for harness noise."""
    if "<command-name>" in text:
        name = _COMMAND_RE.search(text)
        args = _ARGS_RE.search(text)
        parts = [name.group(1).strip() if name else "", args.group(1).strip() if args else ""]
        return " ".join(p for p in parts if p) or None
    if text.lstrip().startswith(("<local-command", "<system-reminder>", "<command-message>")):
        return None
    return text


def _quote(text: str) -> str:
    return "\n".join(f"> {line}".rstrip() for line in text.strip().splitlines())


def render(events: list[dict]) -> str:
    """Turn transcript events into markdown lines."""
    chunks: list[str] = []
    for event in events:
        kind = event.get("type")
        if kind not in ("user", "assistant"):
            continue
        if event.get("isMeta") or event.get("isSidechain") or event.get("parent_tool_use_id"):
            continue
        message = event.get("message") or {}
        content = message.get("content")
        blocks = [{"type": "text", "text": content}] if isinstance(content, str) else (content or [])
        for block in blocks:
            if not isinstance(block, dict):
                continue
            btype = block.get("type")
            if btype == "text":
                text = block.get("text") or ""
                if not text.strip():
                    continue
                if kind == "user":
                    typed = _user_text(text)
                    if typed:
                        chunks.append(_quote(typed))
                else:
                    chunks.append(text.strip())
            elif btype == "tool_use" and kind == "assistant":
                chunks.append(_tool_summary(block.get("name", "?"), block.get("input")))
    return "\n\n".join(chunks) + "\n" if chunks else ""


DROPPED_TYPES = ("system", "rate_limit_event")


def drop_system(lines):
    """Yield the JSONL lines that are not setup events. Lines that do not parse are kept."""
    for line in lines:
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            yield line
            continue
        if isinstance(event, dict) and event.get("type") in DROPPED_TYPES:
            continue
        yield line


def strip_system(path: Path) -> None:
    """Rewrite a JSONL file in place without its setup events."""
    path = Path(path)
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    path.write_text("".join(drop_system(lines)), encoding="utf-8")


def _read_jsonl(path: Path) -> list[dict]:
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def main(argv: list[str]) -> int:
    if argv and argv[0] == "--strip-system":
        if len(argv) == 1:
            for line in drop_system(sys.stdin):
                sys.stdout.write(line)
            sys.stdout.flush()
        for name in argv[1:]:
            strip_system(Path(name))
        return 0
    if len(argv) != 2:
        print("usage: render_transcript.py <in.jsonl> <out.md>", file=sys.stderr)
        return 2
    src, dst = Path(argv[0]), Path(argv[1])
    dst.write_text(render(_read_jsonl(src)), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
