"""Skill lint (every skills/*/SKILL.md) and eval case structure (every evals/<skill>/).

Used by every later skill task: a new skill passes these or it does not ship.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

import _yamlio
from _banned import BANNED_RE, EM_DASH_RE, LLNCS_RE

REPO = Path(__file__).resolve().parent.parent
SKILLS = sorted(d for d in (REPO / "skills").iterdir() if d.is_dir() and not d.name.startswith("_"))
HIDDEN = {"onboard", "commit", "deep-audit", "learn", "checkpoint", "compress-session"}
DESCRIPTION_MAX = 1536
BODY_MAX_LINES = 500
PLUGIN_PATH_RE = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}/([A-Za-z0-9_./-]+)")

# Eval case format (claude plugin eval, checked against Claude Code 2.1.312).
PROMPT_KEYS = {"schema_version", "name", "description", "tags", "plugins", "runs", "expected_outcome",
               "model", "max_turns", "timeout_seconds", "allowed_tools", "disallowed_tools",
               "artifact_publish", "growthbook_overrides", "append_system_prompt", "env"}
GRADER_KEYS = {
    "regex": {"type", "target", "pattern", "flags", "match", "weight", "arm"},
    "tool_order": {"type", "before", "after", "weight", "arm"},
    "tool_used": {"type", "tool", "input_match", "min", "max", "weight", "arm"},
    "file_exists": {"type", "path", "exists", "weight", "arm"},
    "llm": {"type", "criteria", "focus", "weight", "arm"},
    "baseline": {"type", "baseline_file", "criteria", "weight", "arm"},
}
CASE_TOP_KEYS = {"schema_version", "name", "description", "tags", "plugins", "context", "execution",
                 "runs", "graders", "expected_outcome"}


def split_frontmatter(text: str) -> tuple[dict, str]:
    lines = text.splitlines()
    assert lines and lines[0] == "---", "frontmatter must open on line 1"
    end = lines.index("---", 1)
    data = _yamlio.loads_yaml("\n".join(lines[1:end])) or {}
    assert isinstance(data, dict)
    return data, "\n".join(lines[end + 1:])


def _skill_files(d: Path) -> list[Path]:
    return sorted(p for p in d.rglob("*.md") if p.is_file())


def test_there_are_skills():
    assert {d.name for d in SKILLS} >= {"onboard", "doctor", "status", "help"}


@pytest.mark.parametrize("d", SKILLS, ids=lambda d: d.name)
def test_skill_frontmatter(d):
    fm, body = split_frontmatter((d / "SKILL.md").read_text(encoding="utf-8"))
    assert fm.get("name") == d.name
    desc = fm.get("description")
    assert isinstance(desc, str) and 0 < len(desc) < DESCRIPTION_MAX
    assert fm.get("allowed-tools"), "allowed-tools missing"
    assert len(body.splitlines()) < BODY_MAX_LINES
    if d.name in HIDDEN:
        assert fm.get("disable-model-invocation") is True
    if "$ARGUMENTS" in body:
        assert fm.get("argument-hint"), "a skill reading $ARGUMENTS declares argument-hint"


@pytest.mark.parametrize("d", SKILLS, ids=lambda d: d.name)
def test_skill_text_is_generic_and_clean(d):
    for p in _skill_files(d):
        text = p.read_text(encoding="utf-8")
        assert not BANNED_RE.search(text), f"{p}: banned term {BANNED_RE.search(text).group(0)!r}"
        assert not LLNCS_RE.search(text), f"{p}: names the llncs class"
        assert not EM_DASH_RE.search(text), f"{p}: em-dash or en-dash"
        assert "extraction/" not in text, f"{p}: references extraction/"


@pytest.mark.parametrize("d", SKILLS, ids=lambda d: d.name)
def test_plugin_paths_exist(d):
    for p in _skill_files(d):
        for rel in PLUGIN_PATH_RE.findall(p.read_text(encoding="utf-8")):
            rel = rel.rstrip(".")
            assert (REPO / rel).exists(), f"{p}: ${{CLAUDE_PLUGIN_ROOT}}/{rel} does not exist"


def test_lint_catches_a_bad_skill(tmp_path):
    """The lint regexes fire on what they claim to catch (falsifiable)."""
    assert EM_DASH_RE.search("a — b") and BANNED_RE.search("Soccer data")
    assert PLUGIN_PATH_RE.findall('python3 "${CLAUDE_PLUGIN_ROOT}/scripts/nope.py" x') == ["scripts/nope.py"]
    bad = tmp_path / "SKILL.md"
    bad.write_text("---\nname: x\n---\nbody\n")
    fm, _ = split_frontmatter(bad.read_text())
    assert fm.get("allowed-tools") is None


# ---------------------------------------------------------------- evals

@pytest.mark.parametrize("d", SKILLS, ids=lambda d: d.name)
def test_every_skill_has_an_eval_case(d):
    case = REPO / "evals" / d.name
    assert (case / "prompt.md").is_file(), f"evals/{d.name}/prompt.md missing"
    graders = {p.stem: split_frontmatter(p.read_text(encoding="utf-8"))[0]
               for p in (case / "graders").glob("*.md")}
    used = [g for g in graders.values() if g.get("type") == "tool_used" and g.get("tool") == "Skill"]
    assert used and all(d.name in str(g.get("input_match", "")) for g in used)
    assert any(g.get("type") == "llm" for g in graders.values()), "an llm rubric grader"


EVAL_CASES = sorted(p.parent for p in (REPO / "evals").glob("*/prompt.md"))


@pytest.mark.parametrize("case", EVAL_CASES, ids=lambda c: c.name)
def test_eval_prompt_frontmatter(case):
    fm, body = split_frontmatter((case / "prompt.md").read_text(encoding="utf-8"))
    assert set(fm) <= PROMPT_KEYS, set(fm) - PROMPT_KEYS
    assert isinstance(fm.get("max_turns"), int) and 0 < fm["max_turns"] <= 200
    assert isinstance(fm.get("allowed_tools"), list) and "Skill" in fm["allowed_tools"]
    assert body.strip() and "TODO" not in body


@pytest.mark.parametrize("case", EVAL_CASES, ids=lambda c: c.name)
def test_eval_graders(case):
    files = sorted((case / "graders").glob("*.md"))
    assert files
    for p in files:
        fm, body = split_frontmatter(p.read_text(encoding="utf-8"))
        kind = fm.get("type")
        assert kind in GRADER_KEYS, f"{p}: type {kind!r}"
        assert set(fm) <= GRADER_KEYS[kind], f"{p}: unknown keys {set(fm) - GRADER_KEYS[kind]}"
        if kind in ("llm", "baseline"):
            assert body.strip() or fm.get("criteria"), f"{p}: empty rubric"
            assert "TODO" not in body
        if kind == "tool_used":
            assert fm.get("tool")
        if kind == "regex":
            assert body.strip() or fm.get("pattern")
        if kind == "file_exists":
            assert fm.get("path")
        assert not EM_DASH_RE.search(body) and not BANNED_RE.search(body)


@pytest.mark.parametrize("case", EVAL_CASES, ids=lambda c: c.name)
def test_eval_case_yaml(case):
    path = case / "case.yaml"
    if not path.exists():
        return
    data = _yamlio.load_yaml(path)
    assert isinstance(data, dict) and set(data) <= CASE_TOP_KEYS
    assert str(data.get("schema_version")) in {"1", "1.1"}
    ctx = data.get("context") or {}
    for rel in ctx.get("add_dirs", []):
        target = case / rel
        assert target.is_dir(), f"{case.name}: add_dir {rel} is not a directory"
        resolved = target.resolve()
        assert resolved == REPO or REPO in resolved.parents, "add_dirs must stay inside the plugin"
    if ctx.get("scaffold_script"):
        assert (case / ctx["scaffold_script"]).is_file()


def test_validate_bib_semantic_run_uses_a_ten_minute_bash_timeout():
    """A semantic run on a large bibliography outlives the default 2-minute Bash timeout."""
    text = (REPO / "skills" / "validate-bib" / "SKILL.md").read_text(encoding="utf-8")
    assert "600000 ms" in text and "480 s" in text
