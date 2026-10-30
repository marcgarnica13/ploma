"""Host adapters for ploma: render the agents for hosts that cannot load agents/*.md (spec section 9).

Claude Code loads agents/<name>.md from the plugin as is. Codex reads one TOML role file per agent
from the repo's .codex/agents/, so onboard writes .codex/agents/ploma-<name>.toml (mode enforced)
holding a `## ploma host context` block and the agent body verbatim. Paths in the files are
relative to the repo root, so the files are machine-neutral and committed with the project.

Usage:
  python3 scripts/host_adapters.py [--json] build-check

build-check renders every agent for Codex against examples/sample-paper and parses each result
(with tomllib when available, else it checks the three keys are present).

Exit codes: 0 ok, 1 a rendered file failed to parse (the file is named), 2 usage error.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _yamlio  # noqa: E402
import host  # noqa: E402
import profiles  # noqa: E402

SOURCES = Path(__file__).resolve().parent.parent / "agents"
SAMPLE = Path(__file__).resolve().parent.parent / "examples" / "sample-paper"
KEYS = ("name", "description", "developer_instructions")
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
_QUOTES_RE = re.compile(r'"{3,}')


def parse_agent(path: Path) -> tuple[dict, str]:
    """Frontmatter dict and the body after the closing `---` of an agents/*.md file."""
    lines = Path(path).read_text(encoding="utf-8").splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != "---":
        raise ValueError(f"{path}: frontmatter must open on line 1")
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].rstrip("\r\n") == "---")
    except StopIteration:
        raise ValueError(f"{path}: frontmatter is not closed") from None
    data = _yamlio.loads_yaml("".join(lines[1:end])) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: frontmatter is not a mapping")
    return data, "".join(lines[end + 1:])


def _profile_path(kind: str, key: str, root: Path) -> str:
    project_dir = profiles._dirs(kind, Path(root))[0]
    if (project_dir / f"{key}.yaml").is_file():
        return f"ploma.d/{kind}/{key}.yaml"
    return f"{host.LINK}/{kind}/{key}.yaml"


def host_context(cfg: dict, root: Path) -> str:
    """The `## ploma host context` block: plugin paths and the resolved venue and discipline files."""
    venue = (cfg.get("venue") or {}).get("profile")
    discipline = (cfg.get("document") or {}).get("discipline") or "generic"
    venue_line = _profile_path("venues", venue, root) if venue else "none configured"
    return "\n".join([
        "## ploma host context",
        "",
        f"ploma root: {host.LINK}",
        f"ploma scripts: {host.LINK}/scripts",
        f"venue profile: {venue_line}",
        f"discipline card: {_profile_path('disciplines', discipline, root)}",
        "Paths are relative to the repo root. Read ploma.yaml there for the project facts.",
    ])


def _toml_basic(s: str) -> str:
    """A single-line TOML basic string; JSON escapes are valid TOML escapes."""
    return json.dumps(s, ensure_ascii=False)


def _escape_quote_run(m: re.Match) -> str:
    n = len(m.group(0))
    return '""\\"' * (n // 3) + '"' * (n % 3)


def _toml_multiline(s: str) -> str:
    """A TOML basic multi-line string whose parsed value is s.

    Backslashes are doubled, every `\"\"\"` becomes `\"\"\\"`, and control characters other than tab
    and newline are written as \\uXXXX. The newline after the opening delimiter is trimmed by TOML.
    """
    escaped = s.replace("\\", "\\\\")
    escaped = _QUOTES_RE.sub(_escape_quote_run, escaped)
    escaped = _CONTROL_RE.sub(lambda m: f"\\u{ord(m.group(0)):04x}", escaped)
    return '"""\n' + escaped + '"""'


def render_agents(host_: host.Host, cfg: dict, root: Path, sources: Path = SOURCES) -> list:
    """Project files for the host's agents: Codex TOML role files, sorted by name; [] for other hosts."""
    from project_files import FileSpec  # not at module level: project_files imports this module

    if host_.name != "codex" or not host_.agents_dir:
        return []
    context = host_context(cfg, root)
    specs = []
    for src in sorted(Path(sources).glob("*.md"), key=lambda p: p.stem):
        fm, body = parse_agent(src)
        name = f"ploma-{src.stem}"
        instructions = context + "\n\n" + body.lstrip("\r\n")
        content = (f"name = {_toml_basic(name)}\n"
                   f"description = {_toml_basic(str(fm.get('description', '')))}\n"
                   f"developer_instructions = {_toml_multiline(instructions)}\n")
        specs.append(FileSpec(path=f"{host_.agents_dir}/{name}.toml", mode="enforced", content=content))
    return specs


def _check(content: str) -> str | None:
    """None when content parses as the expected TOML, else the error."""
    try:
        import tomllib
    except ModuleNotFoundError:  # Python 3.10: only check the keys appear as lines
        missing = [k for k in KEYS if not re.search(rf"^{k} = ", content, flags=re.M)]
        return f"missing keys {missing}" if missing else None
    try:
        data = tomllib.loads(content)
    except tomllib.TOMLDecodeError as exc:
        return str(exc)
    missing = [k for k in KEYS if not isinstance(data.get(k), str)]
    return f"missing keys {missing}" if missing else None


def build_check() -> tuple[bool, list[str], list[str]]:
    import ploma_config

    specs = render_agents(host.HOSTS["codex"], ploma_config.load(SAMPLE), SAMPLE)
    errors = [f"{s.path}: {err}" for s in specs if (err := _check(s.content))]
    if not specs:
        errors.append(f"no agents rendered from {SOURCES}")
    return not errors, [s.path for s in specs], errors


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("command", choices=("build-check",))
    args = ap.parse_args(argv)
    try:
        ok, files, errors = build_check()
    except Exception as exc:  # a broken source or config is a failed check, named
        ok, files, errors = False, [], [f"{type(exc).__name__}: {exc}"]
    if args.json:
        print(json.dumps({"ok": ok, "files": files, "errors": errors} if not ok else {"ok": True, "files": files}))
    else:
        for err in errors:
            print(f"FAIL {err}", file=sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
