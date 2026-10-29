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
    if d.name == "onboard":
        # A slash-command prompt does not register as a Skill tool call; a regex on the dry-run line grades it.
        assert any(g.get("type") == "regex" for g in graders.values())
    else:
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


# R104: grows with each milestone-2 skill task.
INSTALLED = {"onboard", "doctor", "status", "help", "compile", "validate-bib",
             "audit-reproducibility", "proofread", "verify-claims"}
_PLOMA_CMD = re.compile(r"/ploma:([a-z][a-z-]*)")


def _planned_mention_problems(text: str, label: str) -> list[str]:
    """Every /ploma:<name> is installed, or is followed by "(planned" or "arrives in milestone 2"."""
    problems = []
    for m in _PLOMA_CMD.finditer(text):
        name = m.group(1)
        if name in INSTALLED:
            continue
        after = text[m.end():m.end() + 40].lstrip("`")
        if not re.match(r"\s*(?:\(planned|arrives in milestone 2)", after):
            problems.append(f"{label}: /ploma:{name} is not installed and is not marked (planned")
    return problems


def test_uninstalled_skills_are_marked_planned():
    """Templates, eager rules, hooks and compile output never send the user to a skill that is not installed."""
    files = [p for p in (REPO / "templates").rglob("*") if p.is_file()]
    files += sorted((REPO / "rules" / "eager").glob("*.md"))
    files += sorted((REPO / "hooks").glob("*.py")) + [REPO / "scripts" / "compile.py", REPO / "skills" / "compile" / "SKILL.md"]
    problems = []
    for p in files:
        problems += _planned_mention_problems(p.read_text(encoding="utf-8"), str(p.relative_to(REPO)))
    assert not problems, "\n".join(problems)


def test_planned_check_catches_a_bare_planned_command():
    assert _planned_mention_problems("Run /ploma:format next.", "x")
    assert not _planned_mention_problems("/ploma:format (planned, milestone 2) gives the map.", "x")
    assert not _planned_mention_problems("trim manually; /ploma:format arrives in milestone 2", "x")
    assert not _planned_mention_problems("Run /ploma:compile next.", "x")


# ---------------------------------------------------------------- eval setup (R91)

SCAFFOLD_CASES = ("audit-reproducibility", "compile", "doctor", "onboard", "proofread", "status", "validate-bib",
                  "verify-claims")


def test_evals_contain_no_symlinks():
    """The eval runner refuses symlinks in case directories (R91)."""
    links = [str(p.relative_to(REPO)) for p in (REPO / "evals").rglob("*") if p.is_symlink()]
    assert not links, links


def test_eval_results_are_gitignored():
    lines = (REPO / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "evals/results/" in lines


@pytest.mark.parametrize("name", SCAFFOLD_CASES)
def test_eval_case_scaffold_copies_and_cleans_the_sample(name):
    case = REPO / "evals" / name
    data = _yamlio.load_yaml(case / "case.yaml")
    assert data["context"] == {"scaffold_script": "scaffold.sh"}
    text = (case / "scaffold.sh").read_text(encoding="utf-8")
    assert '"$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/../../examples/sample-paper"' in text
    assert 'cp -R "$src/." .' in text
    assert "rm -rf .ploma quality_reports build main.pdf main.log main.aux main.bbl main.blg" in text
    assert ("rm -f ploma.yaml" in text) == (name == "onboard")


@pytest.mark.parametrize("name", SCAFFOLD_CASES)
def test_eval_scaffold_runs(name, tmp_path):
    import shutil
    import subprocess
    if shutil.which("bash") is None:
        pytest.skip("bash not installed")
    (tmp_path / "main.log").write_text("stale")
    subprocess.run(["bash", str(REPO / "evals" / name / "scaffold.sh")], cwd=tmp_path, check=True, timeout=30)
    assert (tmp_path / "main.tex").is_file() and (tmp_path / "refs.bib").is_file()
    assert not (tmp_path / "main.log").exists() and not (tmp_path / "quality_reports").exists()
    assert (tmp_path / "ploma.yaml").exists() == (name != "onboard")


@pytest.mark.parametrize("name", ("audit-reproducibility", "compile", "doctor", "proofread", "status", "validate-bib",
                                  "verify-claims"))
def test_eval_prompts_are_plain_language(name):
    _, body = split_frontmatter((REPO / "evals" / name / "prompt.md").read_text(encoding="utf-8"))
    assert "/ploma:" not in body and len(body.split()) >= 5


def test_onboard_eval_grades_the_dry_run_statement():
    _, prompt = split_frontmatter((REPO / "evals" / "onboard" / "prompt.md").read_text(encoding="utf-8"))
    assert prompt.strip() == "/ploma:onboard --dry-run"
    fm, body = split_frontmatter((REPO / "evals" / "onboard" / "graders" / "dry_run_statement.md").read_text(encoding="utf-8"))
    assert fm["type"] == "regex"
    skill = (REPO / "skills" / "onboard" / "SKILL.md").read_text(encoding="utf-8")
    statement = re.search(r'Say "(dry run:[^"]*)"', skill).group(1)
    flags = re.I if "i" in str(fm.get("flags", "")) else 0
    assert re.search(body.strip(), statement, flags)
    assert re.search(body.strip(), "Dry run: nothing written.", flags)


# ---------------------------------------------------------------- shared skill references (milestone 2, Task 2)

SHARED = REPO / "skills" / "_shared" / "references"
SHARED_FILES = ("cove.md", "finding-format.md", "report-header.md")


@pytest.mark.parametrize("name", SHARED_FILES)
def test_shared_reference_is_generic_and_clean(name):
    p = SHARED / name
    text = p.read_text(encoding="utf-8")
    assert not BANNED_RE.search(text) and not LLNCS_RE.search(text), name
    assert not EM_DASH_RE.search(text), f"{name}: em-dash or en-dash"
    assert "extraction/" not in text and "context: fork" not in text and "context=fork" not in text
    for rel in PLUGIN_PATH_RE.findall(text):
        assert (REPO / rel.rstrip(".")).exists(), f"{name}: {rel} does not exist"


def test_cove_reference_isolates_the_verifier():
    text = (SHARED / "cove.md").read_text(encoding="utf-8")
    assert "ploma:claim-verifier" in text
    for step in ("Draft", "Extract claims", "verification questions", "fresh context"):
        assert step in text, step
    for outcome in ("PASS", "PARTIAL", "FAIL", "Fail closed"):
        assert outcome in text
    assert "## Post-flight verification" in text  # the output block
    assert "never the draft" in text.lower() or "never pass the draft" in text.lower()
    assert "`partial` with no tier (a reasonable gloss of the source) | counts toward PARTIAL" in text
    assert "`not-verifiable-claim-type` | excluded from the claim count" in text
    assert "### Not verifiable (claim type)" in text


def test_finding_format_names_the_four_fields():
    text = (SHARED / "finding-format.md").read_text(encoding="utf-8")
    for field in ("Location", "Current", "Fix", "Severity"):
        assert f"**{field}:**" in text
    for level in ("CRITICAL", "MAJOR", "MINOR"):
        assert level in text


def test_report_header_fields():
    text = (SHARED / "report-header.md").read_text(encoding="utf-8")
    for field in ("**Date:**", "**File:**", "**Skill:**", "**Config:**"):
        assert field in text


# ---------------------------------------------------------------- validate stage (milestone 2, Tasks 4 and 8)

VALIDATE_SKILLS = ("audit-reproducibility", "proofread", "verify-claims")


def _skill(name: str) -> str:
    return (REPO / "skills" / name / "SKILL.md").read_text(encoding="utf-8")


@pytest.mark.parametrize("name", VALIDATE_SKILLS)
def test_validate_skills_are_installed_and_not_marked_planned(name):
    """R104: the installed set holds the skill and no planned list names it."""
    assert name in INSTALLED and (REPO / "skills" / name / "SKILL.md").is_file()
    help_text = _skill("help")
    planned_help = help_text.split("## Milestone 2 (not yet installed, don't invoke)", 1)[1].split("\n\n")[1]
    assert name not in planned_help.split(", ") and f"{name}," not in planned_help
    assert f"/ploma:{name}" in help_text.split("## Installed now", 1)[1].split("##", 1)[0]
    section = (REPO / "templates" / "claude-md-section.md").read_text(encoding="utf-8")
    planned_line = next(line for line in section.splitlines() if line.startswith("- Planned"))
    installed_line = next(line for line in section.splitlines() if line.startswith("- Installed skills"))
    assert name not in planned_line and f"/ploma:{name}" in installed_line
    core = (REPO / "rules" / "eager" / "00-core.md").read_text(encoding="utf-8")
    assert re.search(rf"Installed now:[^;]*\b{re.escape(name)}\b", core)
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    assert not re.search(rf"/ploma:{re.escape(name)}`? \(planned", readme)
    row = next(line for line in readme.splitlines() if line.startswith("| 6 | Validate"))
    assert not re.search(rf"planned:[^|]*/ploma:{re.escape(name)}\b", row) and f"/ploma:{name}" in row


def test_no_installed_skill_is_called_planned_anywhere():
    files = [REPO / "README.md", REPO / "skills" / "validate-bib" / "SKILL.md"]
    files += [p for p in (REPO / "templates").rglob("*") if p.is_file()]
    files += sorted((REPO / "rules").rglob("*.md")) + sorted((REPO / "skills").rglob("*.md"))
    for p in files:
        text = p.read_text(encoding="utf-8")
        for name in VALIDATE_SKILLS:
            assert not re.search(rf"/ploma:{re.escape(name)}`?,? (?:\(planned|which arrives in milestone 2|arrives in milestone 2)",
                                 text), f"{p}: {name} still marked planned"


def test_audit_reproducibility_contract():
    text = _skill("audit-reproducibility")
    assert "pipeline is not enabled in ploma.yaml; set pipeline.enabled and its keys, or run /ploma:onboard" in text
    assert 'python3 "${CLAUDE_PLUGIN_ROOT}/scripts/consistency.py" --root . --record --json' in text
    assert "--passport" in text and "<outputs.dir>/passports/<slug>.yaml" in text
    assert "<outputs.dir>/reproducibility_audit_<slug>.md" in text
    assert 'python3 "${CLAUDE_PLUGIN_ROOT}/scripts/state.py" record audit-reproducibility' in text
    for status in ("PASS", "FAIL", "STALE", "UNVERIFIED"):
        assert status in text
    assert "never delete" in text.lower()
    for key in ("pipeline.tolerances", "pipeline.metric_keys", "pipeline.outputs_dir", "pipeline.rerun",
                "pipeline.env_contract", "pipeline.run_from"):
        assert key in text, key
    assert "Monitor" in text and "run_in_background" in text
    assert "AskUserQuestion" in text
    # Tolerance numbers come from config and the limits rule, never restated here.
    assert not re.search(r"\b0\.0[12]\b|0\.1 ?pp", text)
    ref = (REPO / "skills" / "audit-reproducibility" / "references" / "passport.md").read_text(encoding="utf-8")
    assert "schemas/passport.schema.json" in ref and "never deletes" in ref.lower()


def test_passport_reference_example_validates(tmp_path):
    """The example passport in the reference parses with the fallback loader and passes the schema check."""
    import sys
    sys.path.insert(0, str(REPO / "scripts"))
    import _yamlmini
    import consistency
    ref = (REPO / "skills" / "audit-reproducibility" / "references" / "passport.md").read_text(encoding="utf-8")
    block = re.search(r"```yaml\n(.*?)```", ref, re.S).group(1)
    data = _yamlmini.load(block)
    assert data["claims"] and data["paper"]["slug"]
    p = tmp_path / "main.yaml"
    p.write_text(block, encoding="utf-8")
    findings, info = consistency._passport_findings(p)
    assert not [f for f in findings if f.id == "consistency.passport_invalid"], [f.summary for f in findings]
    assert info["claims"] == len(data["claims"])


def test_proofread_contract():
    text = _skill("proofread")
    assert "ploma:proofreader" in text and "<outputs.dir>/<stem>_report.md" in text
    assert 'python3 "${CLAUDE_PLUGIN_ROOT}/scripts/gate.py" record proofread' in text
    assert "--extra open_high=" in text and "WARN" in text and "PASS" in text
    assert 'python3 "${CLAUDE_PLUGIN_ROOT}/scripts/state.py" record proofread' in text
    assert "never edits" in text.lower() or "never edit" in text.lower()
    for phase in ("Propose", "Approve", "Apply"):
        assert phase in text, phase
    fm, _ = split_frontmatter(text)
    assert "Edit" not in str(fm["allowed-tools"]).replace("Edit,", "")  # no pre-approved edits
    assert "Agent" in str(fm["allowed-tools"])


def test_verify_claims_contract():
    text = _skill("verify-claims")
    assert "ploma:claim-verifier" in text and "skills/_shared/references/cove.md" in text
    assert "<outputs.dir>/verify_claims_<stem>.md" in text
    assert 'python3 "${CLAUDE_PLUGIN_ROOT}/scripts/gate.py" record claims' in text
    assert 'python3 "${CLAUDE_PLUGIN_ROOT}/scripts/state.py" record verify-claims' in text
    assert "HIGH-WARN" in text and "never" in text.lower()
    assert "allowHighWarn" not in text and "--no-fail-closed" not in text
    assert "context: fork" not in text and "context=fork" not in text
    assert "commit anyway" in text  # the gate override replaces the old opt-outs
    fm, _ = split_frontmatter(text)
    assert "Agent" in str(fm["allowed-tools"])


def test_proofread_rule_and_agent_agree_on_the_report_path():
    rule = (REPO / "rules" / "reference" / "proofreading-protocol.md").read_text(encoding="utf-8")
    agent = (REPO / "agents" / "proofreader.md").read_text(encoding="utf-8")
    assert "<outputs.dir>/<stem>_report.md" in rule and "<outputs.dir>/<stem>_report.md" in agent
    assert "_proofread_report.md" not in agent and "proofread_<document.slug>.md" not in rule
