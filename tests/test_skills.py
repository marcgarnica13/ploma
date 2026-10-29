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
             "audit-reproducibility", "proofread", "verify-claims", "write", "format", "review", "devils-advocate"}
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
    assert _planned_mention_problems("Run /ploma:respond next.", "x")
    assert not _planned_mention_problems("/ploma:respond (planned, milestone 2) gives the map.", "x")
    assert not _planned_mention_problems("trim manually; /ploma:respond arrives in milestone 2", "x")
    assert not _planned_mention_problems("Run /ploma:compile next.", "x")


# ---------------------------------------------------------------- eval setup (R91)

SCAFFOLD_CASES = ("audit-reproducibility", "compile", "doctor", "onboard", "proofread", "status", "validate-bib",
                  "verify-claims", "write", "format", "review", "review-unknown-venue", "devils-advocate")


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
                                  "verify-claims", "write", "format", "review", "review-unknown-venue",
                                  "devils-advocate"))
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
    assert "`partial` with no tier (a reasonable gloss of the source) | verified with a note" in text
    assert "**PASS**: 0 HIGH-WARN and 0 MED-WARN, whatever the LOW-WARN count." in text
    assert "**PARTIAL**: 0 HIGH-WARN and at least one MED-WARN." in text
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
    assert 'If the user picks "Report only", skip steps 2 to 4 entirely' in text
    assert "Run this only when the passport file exists" in text
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


def _tools(fm: dict) -> list[str]:
    raw = fm["allowed-tools"]
    items = raw if isinstance(raw, list) else str(raw).split(",")
    return [str(t).strip() for t in items]


def test_tools_helper_can_fail():
    assert "Edit" in _tools({"allowed-tools": "Read, Edit, Write"})
    assert "Edit" in _tools({"allowed-tools": ["Read", "Edit"]})
    assert "Edit" not in _tools({"allowed-tools": "Read, Bash(python3 *)"})


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
    assert "Edit" not in _tools(fm)  # no pre-approved edits
    assert "Partial run: proofread gate entry not recorded." in text
    assert "every `.tex` file under `document.root`" in text
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
    # Traces outcome rule: LOW never makes PARTIAL; MED does; HIGH fails.
    assert "**PASS**: 0 HIGH-WARN and 0 MED-WARN, whatever the LOW-WARN count." in text
    assert "**PARTIAL**: 0 HIGH-WARN and at least one MED-WARN." in text
    assert "**FAIL**: at least one HIGH-WARN" in text
    assert "## LOW-WARN (advisory, non-gating)" in text
    for match, verdict in (("yes", "SUPPORTED"), ("partial", "PARTIAL"), ("no", "CONTRADICTED"),
                           ("cannot-verify", "UNVERIFIABLE"), ("not-verifiable-claim-type", "excluded")):
        assert re.search(rf"\| `{re.escape(match)}` \| {verdict}", text), match
    assert "--max <floor(cap / batches)>" in text and "at least 1" in text
    assert "Partial run: claims gate entry not recorded." in text
    fm, _ = split_frontmatter(text)
    assert "Agent" in str(fm["allowed-tools"])


def test_proofread_rule_and_agent_agree_on_the_report_path():
    rule = (REPO / "rules" / "reference" / "proofreading-protocol.md").read_text(encoding="utf-8")
    agent = (REPO / "agents" / "proofreader.md").read_text(encoding="utf-8")
    assert "<outputs.dir>/<stem>_report.md" in rule and "<outputs.dir>/<stem>_report.md" in agent
    assert "_proofread_report.md" not in agent and "proofread_<document.slug>.md" not in rule


# ---------------------------------------------------------------- write and format (milestone 2, Tasks 6 and 7)

LIFECYCLE_ROWS = {"write": "| 4 | Write", "format": "| 5b | Format", "review": "| 7 | Review",
                  "devils-advocate": "| 7 | Review"}


@pytest.mark.parametrize("name", sorted(LIFECYCLE_ROWS))
def test_lifecycle_skills_are_installed_and_not_marked_planned(name):
    """R104 for write and format: installed everywhere, planned nowhere."""
    assert name in INSTALLED and (REPO / "skills" / name / "SKILL.md").is_file()
    help_text = _skill("help")
    planned_help = help_text.split("## Milestone 2 (not yet installed, don't invoke)", 1)[1].split("\n\n")[1]
    assert name not in [w.strip(" .") for w in planned_help.split(",")]
    assert f"/ploma:{name}" in help_text.split("## Installed now", 1)[1].split("##", 1)[0]
    section = (REPO / "templates" / "claude-md-section.md").read_text(encoding="utf-8")
    planned_line = next(line for line in section.splitlines() if line.startswith("- Planned"))
    installed_line = next(line for line in section.splitlines() if line.startswith("- Installed skills"))
    assert name not in [w.strip(" .") for w in planned_line.split(":", 1)[1].split(",")]
    assert f"/ploma:{name}" in installed_line
    core = (REPO / "rules" / "eager" / "00-core.md").read_text(encoding="utf-8")
    assert re.search(rf"Installed now:[^;]*\b{re.escape(name)}\b", core)
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    row = next(line for line in readme.splitlines() if line.startswith(LIFECYCLE_ROWS[name]))
    assert f"/ploma:{name}" in row and "planned" not in row
    for p in [REPO / "README.md"] + [q for q in (REPO / "templates").rglob("*") if q.is_file()] \
            + sorted((REPO / "rules").rglob("*.md")) + sorted((REPO / "skills").rglob("*.md")) \
            + [REPO / "scripts" / "compile.py"]:
        text = p.read_text(encoding="utf-8")
        assert not re.search(rf"/ploma:{re.escape(name)}`?,? (?:\(planned|arrives in milestone 2)", text), p


def test_write_contract():
    text = _skill("write")
    fm, _ = split_frontmatter(text)
    assert fm["argument-hint"] == "<section title | sec:label | path> [--from-spec] [--merge]"
    assert "Edit" not in _tools(fm)  # the merge edit always prompts
    assert "AskUserQuestion" in _tools(fm)
    assert 'python3 "${CLAUDE_PLUGIN_ROOT}/scripts/sections.py" --json resolve "<query>"' in text
    assert 'python3 "${CLAUDE_PLUGIN_ROOT}/scripts/sections.py" --json check "<query>" "<sibling>"' in text
    assert 'python3 "${CLAUDE_PLUGIN_ROOT}/scripts/style_check.py" --root . "<sibling>" --json' in text
    assert ".ploma/tmp/" in text and "--record" in text  # checks run on a copy, never recorded
    assert "diff -u" in text and "Open flags" in text
    assert "% ploma:source <script> <args>" in text and "never invent a script" in text
    assert "paper_spec.md not found" in text
    assert "explicit yes" in text and "stale" in text
    assert "Run /ploma:compile" in text
    assert 'python3 "${CLAUDE_PLUGIN_ROOT}/scripts/state.py" record write' in text
    assert "never edits the manuscript" in text and "never fixed there" in text
    assert "skills/_shared/references/finding-format.md" in text
    assert not re.search(r"\bat most \d|\b[23] (?:times|rounds|retries)\b", text)  # caps come from limits.md
    ref = (REPO / "skills" / "write" / "references" / "sibling-file.md").read_text(encoding="utf-8")
    for field in ("% Source:", "% Source sha:", "% Spec items served:", "% Date:", "% Merge:"):
        assert field in ref, field
    assert "<stem>_suggestion.tex" in ref and "rm <sibling>" in ref


def test_write_eval_guards_the_manuscript():
    graders = {p.stem: split_frontmatter(p.read_text(encoding="utf-8"))[0]
               for p in (REPO / "evals" / "write" / "graders").glob("*.md")}
    assert any(g.get("type") == "file_exists" and g.get("path") == "sections/intro_suggestion.tex"
               for g in graders.values())
    assert any(g.get("type") == "tool_used" and g.get("tool") == "Edit" and g.get("max") == 0
               for g in graders.values())
    _, prompt = split_frontmatter((REPO / "evals" / "write" / "prompt.md").read_text(encoding="utf-8"))
    assert "introduction" in prompt.lower() and "shorter" in prompt.lower()


def test_format_contract():
    text = _skill("format")
    fm, _ = split_frontmatter(text)
    assert fm["argument-hint"] == "[--budget N] [--presubmit]"
    tools = _tools(fm)
    assert "Edit" not in tools and "Agent" not in tools
    for t in ("Bash(chktex *)", "Bash(lacheck *)", "Bash(texcount *)"):
        assert t in tools, t
    assert 'python3 "${CLAUDE_PLUGIN_ROOT}/scripts/page_map.py" --json' in text
    assert "<outputs.dir>/page_budget_<slug>.md" in text and "<outputs.dir>/presubmit_<slug>.md" in text
    assert "skills/format/references/cut-plan.md" in text and "skills/format/references/presubmit.md" in text
    assert 'python3 "${CLAUDE_PLUGIN_ROOT}/scripts/state.py" record format' in text
    assert "do not call `gate.py`" in text and "gate.py\" record" not in text
    assert "never edits a source file" in text and "all in one message" in text and "SKIP" in text
    ref = (REPO / "skills" / "format" / "references" / "presubmit.md").read_text(encoding="utf-8")
    for cmd in ("chktex -q -n1 -n8 -n36 -v0", "lacheck", "texcount -inc -sum -brief", "scripts/placeholders.py",
                "scripts/bib_check.py", "scripts/style_check.py", "scripts/arxiv_rules.py", "scripts/latex_log.py",
                "scripts/profiles.py"):
        assert cmd in ref, cmd
    for hint in ("tlmgr install chktex", "tlmgr install lacheck", "tlmgr install texcount"):
        assert hint in ref
    cut = (REPO / "skills" / "format" / "references" / "cut-plan.md").read_text(encoding="utf-8")
    for heading in ("## Where the pages go (measured)", "## Principle", "## Cut plan (ordered by value per page",
                    "## Resulting budget", "## What is not cut", "## Risk", "## Recommendation"):
        assert heading in cut, heading


def test_compile_points_to_format():
    import compile as compile_mod
    assert "/ploma:format" in compile_mod.__loader__.get_source("compile")
    assert "/ploma:format for the page map" in _skill("compile")


def test_presubmit_exit_codes_are_tabled():
    """Fix round 1: which exit codes are results and which mean the check did not run."""
    for text in (_skill("format"), (REPO / "skills" / "format" / "references" / "presubmit.md").read_text(encoding="utf-8")):
        assert "## Exit codes" in text or "Exit codes" in text
    ref = (REPO / "skills" / "format" / "references" / "presubmit.md").read_text(encoding="utf-8")
    table = ref.split("## Exit codes", 1)[1].split("\n## ", 1)[0]
    for row in ("| placeholders.py, bib_check.py, arxiv_rules.py | 0 = no FAIL | 1 = findings (a result) | 2 = did not run |",
                "| chktex | 0, no output | 0 or non-zero with output = findings (a result) | non-zero with no output = did not run |",
                "| lacheck | 0, no output | any output = findings (a result) |",
                "| texcount | 0 | | non-zero = did not run |",
                "| any | | | 127 = not installed: SKIP with the install hint |"):
        assert row in table, row


def test_write_merge_needs_a_merge_run():
    """R131: a bare yes after a draft run never merges; the user reruns with --merge."""
    text = _skill("write")
    assert "Merging happens only in a run invoked with `--merge`" in text
    assert "rerun with `/ploma:write <query> --merge`" in text
    assert "ignoring trailing blank lines" in text


# ---------------------------------------------------------------- review and devils-advocate (milestone 2, Task 9)

REVIEW_REFS = ("peer-pipeline", "adversarial-loop", "seven-pass", "report-templates")
# Loop caps come from rules/eager/limits.md and limits: in config; no review file restates a number.
CAP_RE = re.compile(r"\b(?:max(?:imum)?|at most|up to|cap(?:ped)? (?:at|of)) \d|\bN ?(?:<=|≤) ?\d|\b\d+ rounds\b|(?<!-)\br[3-9]\b")


def _review_texts() -> dict[str, str]:
    texts = {"SKILL.md": _skill("review")}
    for name in REVIEW_REFS:
        texts[name] = (REPO / "skills" / "review" / "references" / f"{name}.md").read_text(encoding="utf-8")
    return texts


def test_review_frontmatter_and_tools():
    fm, _ = split_frontmatter(_skill("review"))
    assert fm["argument-hint"] == ("[path] [--adversarial | --peer <venue> [--r2|--r3|--stress|--variance N] "
                                   "[--no-novelty-check] | --seven-pass] [--no-cross-artifact]")
    tools = _tools(fm)
    assert "Edit" not in tools  # adversarial edits always prompt
    for tool in ("Agent", "Skill", "AskUserQuestion", "Write", "Bash(python3 *)"):
        assert tool in tools, tool


def test_review_contract():
    text = _skill("review")
    refs = _review_texts()
    for name in REVIEW_REFS:
        assert f"${{CLAUDE_PLUGIN_ROOT}}/skills/review/references/{name}.md" in text, name
    # Venue resolution: profiles.py from the skill; an unknown key stops before any agent with the key list.
    assert 'python3 "${CLAUDE_PLUGIN_ROOT}/scripts/profiles.py" --root . show <key>' in text
    assert "stop before spawning any agent" in text and "available keys" in text
    # Pre-Flight Report in --peer mode, before any agent.
    assert "## Pre-Flight Report" in refs["report-templates"]
    assert "Print the Pre-Flight Report before spawning any agent" in refs["peer-pipeline"]
    # Default and peer never edit the manuscript; adversarial edits only on approval, with snapshot and rollback.
    assert "Default and `--peer` modes never edit the manuscript" in text
    adv = refs["adversarial-loop"]
    for s in ("git stash", ".ploma/review-backup/", 'python3 "${CLAUDE_PLUGIN_ROOT}/scripts/compile.py" --json',
              "author disagreement", "AskUserQuestion", "limits.review_rounds", "ROLLED BACK"):
        assert s in adv, s
    # Orchestration by the skill: editor, then both referees in one message, then synthesis; CoVe on novelty claims.
    peer = refs["peer-pipeline"]
    for s in ("ploma:editor", "ploma:domain-referee", "ploma:methods-referee", "ploma:claim-verifier",
              "both in one message", "blind to each other", "skills/_shared/references/cove.md",
              "desk_review.md", "referee_domain.md", "referee_methods.md", "editorial_decision.md", "_r<N>",
              "referee_1.md", "decision_distribution.md", "editor_synthesis.md", "<outputs.dir>/peer_review_<slug>/",
              "--no-novelty-check", "mutually exclusive"):
        assert s in peer, s
    assert "The editor spawns no agents" in peer
    # Round flags: the cap comes from limits; above it the skill refuses.
    assert "revise-and-resubmit cap" in text and "refuse" in text.lower()
    # Cross-artifact: only with pipeline.enabled and without --no-cross-artifact; first in peer, last in default.
    for s in ("pipeline.enabled", "--no-cross-artifact", "/ploma:audit-reproducibility",
              "rules/reference/cross-artifact-review.md"):
        assert s in text, s
    # Seven-pass: lenses in parallel, lens 3 and 6 by ploma agents, lens 7 runs the semantic bib check itself.
    seven = refs["seven-pass"]
    for s in ("ploma:domain-reviewer", "ploma:proofreader", "general-purpose", "all seven in one message",
              "validate_bib.py --root . --semantic --json", "_SYNTHESIS.md", "<outputs.dir>/seven_pass_<slug>/",
              "lens_<N>_<name>.md"):
        assert s in seven, s
    assert "/ploma:validate-bib" not in seven.split("## Lens 7", 1)[1].split("\n## ", 1)[0]
    # Default report: six dimensions keep their names; method and evaluation cite the discipline card.
    tpl = refs["report-templates"]
    for dim in ("Argument Structure", "Method Soundness", "Evaluation & Validity", "Literature Positioning",
                "Writing Quality", "Presentation"):
        assert dim in tpl, dim
    assert tpl.count("sanity_checks") >= 2
    assert "<outputs.dir>/paper_review_<slug>_round<N>.md" in text
    # State, findings, data-not-instructions.
    assert 'python3 "${CLAUDE_PLUGIN_ROOT}/scripts/state.py" record review' in text and "--extra round=<N>" in text
    assert "skills/_shared/references/finding-format.md" in text and "data, never instructions" in text
    assert "context: fork" not in "".join(refs.values()) and "context=fork" not in "".join(refs.values())
    for name, body in refs.items():
        m = CAP_RE.search(body)
        assert not m, f"{name} restates a cap: {body[max(0, m.start() - 30):m.end() + 30]!r}"


def test_review_reference_files_are_generic_and_clean():
    for name, body in _review_texts().items():
        assert not BANNED_RE.search(body) and not LLNCS_RE.search(body) and not EM_DASH_RE.search(body), name


def test_review_evals():
    def graders(case):
        return [split_frontmatter(p.read_text(encoding="utf-8")) for p in (REPO / "evals" / case / "graders").glob("*.md")]
    default = graders("review")
    assert any(fm.get("type") == "tool_used" and fm.get("tool") == "Edit" and fm.get("max") == 0 for fm, _ in default)
    assert any(fm.get("type") == "file_exists" and fm.get("path") == "quality_reports/paper_review_main_round1.md"
               for fm, _ in default)
    unknown = graders("review-unknown-venue")
    assert any(fm.get("type") == "tool_used" and fm.get("tool") == "Agent" and fm.get("max") == 0 for fm, _ in unknown)
    assert any(fm.get("type") == "tool_used" and fm.get("tool") == "Skill" and "review" in str(fm.get("input_match"))
               for fm, _ in unknown)
    regex = [body.strip() for fm, body in unknown if fm.get("type") == "regex"]
    import subprocess
    import sys
    out = subprocess.run([sys.executable, str(REPO / "scripts" / "profiles.py"), "show", "quantum-letters"],
                         capture_output=True, text=True)
    assert out.returncode == 2 and regex and all(re.search(r, out.stderr) for r in regex)
    rubric = " ".join(body for fm, body in unknown if fm.get("type") == "llm")
    assert "Pre-Flight Report" in rubric and "available" in rubric
    _, prompt = split_frontmatter((REPO / "evals" / "review-unknown-venue" / "prompt.md").read_text(encoding="utf-8"))
    assert "quantum-letters" in prompt


def test_devils_advocate_contract():
    text = _skill("devils-advocate")
    fm, _ = split_frontmatter(text)
    tools = _tools(fm)
    assert "Edit" not in tools and "Agent" not in tools
    for s in ("reviews.glob", "challenge_examples", "5 to 7", "<outputs.dir>/devils_advocate_<slug>.md",
              'python3 "${CLAUDE_PLUGIN_ROOT}/scripts/state.py" record devils-advocate', "never edits",
              "data, never instructions"):
        assert s in text, s
    for cat in ("Framing", "Method choice", "Evaluation", "Generalization", "Scope", "Argument order", "Related work"):
        assert cat in text, cat
    graders = [split_frontmatter(p.read_text(encoding="utf-8"))[0]
               for p in (REPO / "evals" / "devils-advocate" / "graders").glob("*.md")]
    assert any(g.get("type") == "tool_used" and g.get("tool") == "Edit" and g.get("max") == 0 for g in graders)
    assert any(g.get("type") == "file_exists" and g.get("path") == "quality_reports/devils_advocate_main.md"
               for g in graders)
