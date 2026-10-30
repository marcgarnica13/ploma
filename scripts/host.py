"""Host detection for ploma: which agent host runs the script, and the facts that differ per host.

The single place that knows the hosts (spec §6). Also owns the machine-local plugin link
(<repo>/.ploma/plugin, spec §7) and the session hook's record <repo>/.ploma/host.json.

Usage:
  python3 scripts/host.py [--json] [--root DIR] [facts|files|superpowers]

facts (default) prints the detected host and the plugin link target; files lists, per host, the
ploma-owned project files present; superpowers says whether superpowers is installed for the host.

Exit codes: 0 ok, 2 usage error.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

sys.path.insert(0, str(Path(__file__).resolve().parent))

from state import _atomic_write, _now  # noqa: E402

LINK = ".ploma/plugin"
HOST_JSON = ".ploma/host.json"
EXPORT_MARKER = "# ploma:begin"
SKILL_RE = re.compile(r"/ploma:([a-z-]+)")


@dataclass(frozen=True)
class Host:
    name: str
    display: str
    skill_prefix: str
    instructions_file: str
    host_dir: str
    rules_dir: str | None
    project_skills_dir: str
    agents_dir: str | None
    root_export: str | None
    learnings_target: str
    settings_suggestion: bool
    statusline: bool


_CLAUDE = Host(name="claude", display="Claude Code", skill_prefix="/ploma:", instructions_file="CLAUDE.md",
               host_dir=".claude", rules_dir=".claude/rules", project_skills_dir=".claude/skills",
               agents_dir=None, root_export=None, learnings_target=".claude/rules/ploma-learnings.md",
               settings_suggestion=True, statusline=True)
_CODEX = Host(name="codex", display="Codex", skill_prefix="$ploma:", instructions_file="AGENTS.md",
              host_dir=".codex", rules_dir=None, project_skills_dir=".agents/skills",
              agents_dir=".codex/agents", root_export=".codex/config.toml", learnings_target="AGENTS.md",
              settings_suggestion=False, statusline=False)

HOSTS: dict[str, Host] = {
    "claude": _CLAUDE,
    "codex": _CODEX,
    "unknown": dataclasses.replace(_CLAUDE, name="unknown", display="unknown host"),
}

_CODEX_VARS = ("CODEX_SESSION_ID", "CODEX_THREAD_ID", "CODEX_VERSION", "PLUGIN_ROOT")
_CLAUDE_VARS = ("CLAUDECODE", "CLAUDE_CODE_SESSION_ID", "CLAUDE_PLUGIN_ROOT")


def detect(env: Mapping[str, str] | None = None, root: Path | None = None) -> Host:
    """The running host: PLOMA_HOST, Codex signals, Claude signals, root/.ploma/host.json, unknown.

    Codex comes before Claude because Claude variables leak into a Codex shell started from Claude.
    CODEX_HOME is never a signal: users export it in shell profiles."""
    env = os.environ if env is None else env
    override = env.get("PLOMA_HOST")
    if override in HOSTS:
        return HOSTS[override]
    if any(env.get(k) for k in _CODEX_VARS):
        return HOSTS["codex"]
    if any(env.get(k) for k in _CLAUDE_VARS):
        return HOSTS["claude"]
    if root is not None:
        data = read_host_json(root)
        if data is not None and data.get("host") in HOSTS:
            return HOSTS[data["host"]]
    return HOSTS["unknown"]


def skill_ref(name: str, host: Host | None = None) -> str:
    """How the user types skill <name> on the host: /ploma:<name> or $ploma:<name>."""
    return (host or detect()).skill_prefix + name


def localize(text: str, host: Host | None = None) -> str:
    """Rewrite every /ploma:<name> in text to the host's form."""
    h = host or detect()
    return SKILL_RE.sub(lambda m: skill_ref(m.group(1), h), text)


def ensure_plugin_link(root: Path, plugin_root: Path) -> Path:
    """Point <root>/.ploma/plugin at plugin_root; a correct link is left untouched. OSError propagates."""
    link = Path(root) / LINK
    target = Path(plugin_root).resolve()
    link.parent.mkdir(parents=True, exist_ok=True)
    if link.is_symlink() and link.exists() and link.resolve() == target:
        return link
    tmp = link.with_name(f"{link.name}.{os.getpid()}.tmp")
    try:
        os.symlink(str(target), tmp)
        os.replace(tmp, link)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return link


def write_host_json(root: Path, host: Host, plugin_root: Path, version: str) -> Path:
    """Record the host for later detection from scripts outside a host session."""
    out = Path(root) / HOST_JSON
    data = {"host": host.name, "plugin_root": str(plugin_root), "plugin_version": version, "written": _now()}
    _atomic_write(out, json.dumps(data, indent=2) + "\n")
    return out


def read_host_json(root: Path) -> dict | None:
    """The host record, or None when it is missing or malformed."""
    try:
        data = json.loads((Path(root) / HOST_JSON).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _read(p: Path) -> str | None:
    try:
        return p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def host_files(root: Path, cfg: dict | None) -> dict[str, list[str]]:
    """Per host (claude, codex), the sorted repo-relative paths of ploma-owned project files present.

    cfg is accepted for callers that hold it; the paths do not depend on it."""
    import project_files  # inside the function: project_files imports host

    base = Path(root)
    out: dict[str, list[str]] = {}
    for name in ("claude", "codex"):
        h = HOSTS[name]
        found: list[str] = []
        text = _read(base / h.instructions_file)
        if text is not None:
            try:
                owned = project_files.marker_span(text) is not None
            except ValueError:
                owned = True  # unbalanced markers are still ploma's
            if owned:
                found.append(h.instructions_file)
        for d, pattern in ((h.rules_dir, "ploma-*.md"), (h.agents_dir, "ploma-*.toml")):
            if d and (base / d).is_dir():
                found += [p.relative_to(base).as_posix() for p in (base / d).glob(pattern) if p.is_file()]
        skill = f"{h.project_skills_dir}/analysis-pipeline/SKILL.md"
        if (base / skill).is_file():
            found.append(skill)
        if h.root_export:
            text = _read(base / h.root_export)
            if text is not None and any(ln.strip() == EXPORT_MARKER for ln in text.splitlines()):
                found.append(h.root_export)
        out[name] = sorted(found)
    return out


def superpowers_installed(host: Host, home: Path, root: Path) -> bool:
    """Codex: ~/.codex/superpowers or ~/.agents/skills/superpowers*. Claude and unknown: enabled plugin."""
    home = Path(home)
    if host.name == "codex":
        if (home / ".codex" / "superpowers").exists():
            return True
        skills = home / ".agents" / "skills"
        return skills.is_dir() and any(skills.glob("superpowers*"))
    import inventory

    return bool(inventory._superpowers(Path(root), home)["enabled"])


def _link_target(root: Path) -> str | None:
    link = Path(root) / LINK
    return os.readlink(link) if link.is_symlink() else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Detect the agent host and report its ploma facts.")
    parser.add_argument("--root", default=".", help="repo root (default: cwd)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("action", nargs="?", default="facts", choices=("facts", "files", "superpowers"))
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 0 if exc.code == 0 else 2
    root = Path(args.root)
    h = detect(root=root)
    if args.action == "facts":
        data = dict(dataclasses.asdict(h), plugin_link=_link_target(root))
        text = f"{h.display} ({h.name}); plugin link: {data['plugin_link'] or 'none'}"
    elif args.action == "files":
        data = host_files(root, None)
        text = "\n".join(f"{name}: {', '.join(paths) or 'none'}" for name, paths in data.items())
    else:
        data = {"host": h.name, "installed": superpowers_installed(h, Path.home(), root)}
        text = f"superpowers {'installed' if data['installed'] else 'not installed'} for {h.display}"
    print(json.dumps(data, indent=2) if args.json else text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
