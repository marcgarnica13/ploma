"""commit_gate.py: refresh stale or missing deterministic gate checks, then the commit verdict."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

import commit_gate
import gate
import pdf_pages
import state

REPO = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture(autouse=True)
def _no_poppler(monkeypatch):
    """r2d2 has no pdfinfo or pdftotext; make every machine behave the same."""
    monkeypatch.setattr(pdf_pages, "_which", lambda name: None)


class Runner:
    """Stand-in for the build runner: records calls, drops a fixture log and PDF into place."""

    def __init__(self, root: Path, log: str = "clean.log", returncode: int = 0):
        self.root, self.log, self.returncode = root, log, returncode
        self.calls: list = []

    def __call__(self, cmd, **kw):
        self.calls.append(cmd)
        shutil.copyfile(FIXTURES / "logs" / self.log, self.root / "main.log")
        shutil.copyfile(FIXTURES / "pdf" / "three_pages.pdf", self.root / "main.pdf")
        return subprocess.CompletedProcess(cmd, self.returncode, "", "")


def _touch_tex(root: Path) -> None:
    p = root / "sections" / "intro.tex"
    p.write_text(p.read_text(encoding="utf-8") + "\n% edited\n", encoding="utf-8")


def _all_fresh(root: Path, cfg: dict) -> None:
    for name in ("compile", "bib", "consistency", "claims", "proofread"):
        gate.record(root, cfg, name, "PASS", f"quality_reports/{name}.md")


# ---------------------------------------------------------------- refresh

def test_stale_compile_is_rerun(sample_paper, cfg):
    _all_fresh(sample_paper, cfg)
    before = gate.load(sample_paper, cfg)["checks"]["compile"]
    _touch_tex(sample_paper)
    runner = Runner(sample_paper)
    prep = commit_gate.prepare(sample_paper, cfg, runner=runner)
    assert runner.calls, "the stale compile entry was not rebuilt"
    after = gate.load(sample_paper, cfg)["checks"]["compile"]
    assert after["manuscript_sha"] == gate.manuscript_sha(sample_paper, cfg) != before["manuscript_sha"]
    assert after["artifact"] == "quality_reports/compile_main.md" and after["pages"] == 3
    assert {"compile", "bib", "consistency"} <= set(prep.refreshed)
    assert prep.verdict == "PASS" and not prep.failing


def test_fresh_entries_are_not_rerun(sample_paper, cfg):
    _all_fresh(sample_paper, cfg)
    runner = Runner(sample_paper)
    prep = commit_gate.prepare(sample_paper, cfg, runner=runner)
    assert not runner.calls and prep.refreshed == [] and prep.verdict == "PASS"
    assert prep.warnings == [] and prep.next_commands == []


def test_missing_required_checks_are_produced(sample_paper, cfg):
    runner = Runner(sample_paper)
    prep = commit_gate.prepare(sample_paper, cfg, runner=runner)
    assert prep.refreshed == ["compile", "bib", "consistency"]
    checks = gate.load(sample_paper, cfg)["checks"]
    assert checks["bib"]["mode"] == "structural" and checks["bib"]["status"] == "PASS"
    assert prep.verdict == "PASS"
    assert prep.missing == ["claims", "proofread"] and prep.stale == []
    assert prep.next_commands == ["/ploma:verify-claims", "/ploma:proofread"]
    assert state.load(sample_paper, cfg)["events"][-1]["skill"] in ("compile", "validate-bib")


def test_stale_recommended_checks_get_next_commands(sample_paper, cfg):
    _all_fresh(sample_paper, cfg)
    _touch_tex(sample_paper)
    prep = commit_gate.prepare(sample_paper, cfg, runner=Runner(sample_paper))
    assert prep.stale == ["claims", "proofread"] and prep.missing == []
    assert prep.next_commands == ["/ploma:verify-claims", "/ploma:proofread"]
    assert prep.verdict == "PASS"  # recommended checks never block


def test_stale_gate_halts_before_git(sample_paper, cfg):
    """A re-run compile that FAILs makes the verdict FAIL; the skill stops before any git step."""
    _all_fresh(sample_paper, cfg)
    _touch_tex(sample_paper)
    prep = commit_gate.prepare(sample_paper, cfg, runner=Runner(sample_paper, log="error.log", returncode=2))
    assert prep.verdict == "FAIL"
    assert "compile" in prep.failing and "compile" in prep.refreshed
    assert gate.load(sample_paper, cfg)["checks"]["compile"]["status"] == "FAIL"
    text = (REPO / "skills" / "commit" / "SKILL.md").read_text(encoding="utf-8")
    text = text.split("\n---\n", 1)[1]  # body only: allowed-tools names git commands
    stop = text.index("FAIL or INCOMPLETE")
    first_git = min(m.start() for m in re.finditer(r"^git (?:add|commit|checkout|switch|push)", text, re.M))
    assert stop < first_git, "the gate stop must come before the first git command"
    step0 = text[stop:text.index("\n## ", stop)]
    assert "stop" in step0.lower()


def test_build_that_cannot_run_is_fail(sample_paper, cfg):
    def broken(cmd, **kw):
        raise FileNotFoundError(2, "No such file or directory", "make")
    prep = commit_gate.prepare(sample_paper, cfg, runner=broken)
    assert prep.verdict == "FAIL" and "compile" in prep.failing


def test_bib_fail_is_fail(sample_paper, cfg):
    tex = sample_paper / "sections" / "intro.tex"
    tex.write_text(tex.read_text(encoding="utf-8") + "\nSee \\cite{nosuchkey2099}.\n", encoding="utf-8")
    prep = commit_gate.prepare(sample_paper, cfg, runner=Runner(sample_paper))
    assert prep.verdict == "FAIL" and prep.failing == ["bib"]


def test_consistency_is_run_by_prepare(sample_paper, cfg):
    _all_fresh(sample_paper, cfg)
    _touch_tex(sample_paper)
    prep = commit_gate.prepare(sample_paper, cfg, runner=Runner(sample_paper))
    assert "consistency" in prep.refreshed
    entry = gate.load(sample_paper, cfg)["checks"]["consistency"]
    assert entry["manuscript_sha"] == gate.manuscript_sha(sample_paper, cfg)
    assert entry["artifact"] == "quality_reports/consistency_main.md"
    assert (sample_paper / "quality_reports" / "consistency_main.md").is_file()


def test_consistency_fail_only_warns(sample_paper, cfg):
    main = sample_paper / "main.tex"
    main.write_text(main.read_text(encoding="utf-8").replace("fitness of 0.81", "fitness of 0.97"), encoding="utf-8")
    prep = commit_gate.prepare(sample_paper, cfg, runner=Runner(sample_paper))
    assert gate.load(sample_paper, cfg)["checks"]["consistency"]["status"] == "FAIL"
    assert prep.verdict == "PASS" and prep.failing == []
    assert any(w.startswith("consistency: FAIL") for w in prep.warnings)


def test_to_dict_is_json(sample_paper, cfg):
    prep = commit_gate.prepare(sample_paper, cfg, runner=Runner(sample_paper))
    data = json.loads(json.dumps(prep.to_dict()))
    assert set(data) >= {"verdict", "refreshed", "stale", "missing", "failing", "warnings",
                         "can_override", "override_streak", "next_commands"}


# ---------------------------------------------------------------- override

@pytest.mark.parametrize("message,reason", [
    ("commit anyway: camera-ready deadline", "camera-ready deadline"),
    ("Commit Anyway:   reviewer asked for it today  ", "reviewer asked for it today"),
    ("ok then, COMMIT ANYWAY: build server is down", None),
    ("do not commit anyway: x", None),
    ("thanks.\n  COMMIT ANYWAY: build server is down\nmore text", "build server is down"),
    ("commit anyway:", None),
    ("commit anyway:    ", None),
    ("commit anyway", None),
    ("please commit", None),
    ("", None),
])
def test_parse_override(message, reason):
    assert commit_gate.parse_override(message) == reason


def test_override_refused_after_three(sample_paper, cfg, capsys):
    prep = commit_gate.prepare(sample_paper, cfg, runner=Runner(sample_paper, log="error.log", returncode=2))
    assert prep.verdict == "FAIL" and prep.can_override and prep.override_streak == 0
    root = str(sample_paper)
    for i in range(3):
        assert commit_gate.main(["--root", root, "override", "--reason", f"deadline {i}"]) == 0
    data = gate.load(sample_paper, cfg)
    assert data["override_streak"] == 3 and data["overrides"][-1]["checks"] == ["compile"]
    capsys.readouterr()
    assert commit_gate.main(["--root", root, "override", "--reason", "one more"]) == 1
    assert "consecutive" in capsys.readouterr().err
    prep = commit_gate.prepare(sample_paper, cfg, runner=Runner(sample_paper, log="error.log", returncode=2))
    assert not prep.can_override and prep.override_streak == 3


def test_override_needs_a_failing_gate(sample_paper, cfg, capsys):
    _all_fresh(sample_paper, cfg)
    assert commit_gate.main(["--root", str(sample_paper), "override", "--reason", "x"]) == 1
    assert "nothing to override" in capsys.readouterr().err
    assert gate.load(sample_paper, cfg)["override_streak"] == 0


# ---------------------------------------------------------------- CLI

def _set_build(root: Path, command: str) -> None:
    p = root / "ploma.yaml"
    p.write_text(p.read_text(encoding="utf-8").replace('command: "make"', f'command: "{command}"'), encoding="utf-8")


def test_cli_prepare_json_fail_exit_1(sample_paper, capsys):
    _set_build(sample_paper, "exit 3")
    assert commit_gate.main(["--root", str(sample_paper), "prepare", "--json"]) == 1
    data = json.loads(capsys.readouterr().out)
    assert data["verdict"] == "FAIL" and "compile" in data["failing"]


def test_cli_prepare_text_pass_exit_0(sample_paper, cfg, capsys):
    _all_fresh(sample_paper, cfg)
    assert commit_gate.main(["--root", str(sample_paper), "prepare"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("commit gate: PASS")


def test_cli_usage_errors(tmp_path, capsys):
    assert commit_gate.main([]) == 2
    assert commit_gate.main(["--root", str(tmp_path), "prepare"]) == 2
    assert commit_gate.main(["--root", str(tmp_path), "override"]) == 2


# ---------------------------------------------------------------- skill and eval contract

def _skill_text() -> str:
    return (REPO / "skills" / "commit" / "SKILL.md").read_text(encoding="utf-8")


def test_commit_skill_contract():
    import _yamlio
    text = _skill_text()
    fm = _yamlio.loads_yaml(text.split("\n---\n", 1)[0].removeprefix("---\n"))
    assert fm["disable-model-invocation"] is True
    assert fm["argument-hint"] == "[message] [--branch <name>] [--no-pr]"
    body = text.split("\n---\n", 1)[1]
    for s in ("commit_gate.py\" prepare --json", "override --json --reason-file - <<'PLOMA_REASON'", "check-override --json <<'PLOMA_MESSAGE'", "`commit anyway: <reason>`",
              "can_override", "ploma-override: <reason>", "doctor.py", "NOT_READY", "git status --porcelain",
              "git add -- <path1>", "Never `git add -A`, `git add .`", "Never force-push", "never merge a pull request",
              "--no-pr", "command -v gh", "AskUserQuestion", "state.py\" record commit", "next_commands",
              "\"Commit fix-and-recheck rounds\"", "\"Consecutive commit overrides\"",
              "attribution lines the session's instructions ask for", "600000 ms"):
        assert s in body, s
    assert not re.search(r"git add (?:-A|\.)(?:\s|$)", body.replace("`git add -A`", "").replace("`git add .`", ""))
    assert "--force" not in body and "--no-verify`)" in body
    assert body.index("## Step 0b: Doctor") < body.index("## Step 1:")


def test_commit_skill_restates_no_cap():
    body = _skill_text().split("\n---\n", 1)[1]
    assert not re.search(r"\b(?:two|three|2|3) (?:rounds|consecutive|overrides|times)\b", body, re.I)
    limits = (REPO / "rules" / "eager" / "limits.md").read_text(encoding="utf-8")
    assert "| Commit fix-and-recheck rounds | 2 |" in limits
    assert f"| Consecutive commit overrides | {gate.MAX_CONSECUTIVE_OVERRIDES} |" in limits


def test_commit_eval_halts_without_git_writes(tmp_path):
    import _yamlio
    case = REPO / "evals" / "commit"
    assert _yamlio.load_yaml(case / "case.yaml")["context"] == {"scaffold_script": "scaffold.sh"}
    graders = {p.stem: p.read_text(encoding="utf-8") for p in (case / "graders").glob("*.md")}
    for name in ("no_git_add", "no_git_commit", "no_push"):
        assert "max: 0" in graders[name]
    assert "commit_gate.py" in graders["gate_ran"] and "min: 1" in graders["gate_ran"]
    if shutil.which("bash") is None or shutil.which("git") is None:
        pytest.skip("bash or git not installed")
    (tmp_path / "main.log").write_text("stale")
    subprocess.run(["bash", str(case / "scaffold.sh")], cwd=tmp_path, check=True, timeout=60)
    assert not (tmp_path / "main.log").exists()
    assert (tmp_path / ".git").is_dir() and (tmp_path / "quality_reports" / "ploma-receipt.json").is_file()
    status = subprocess.run(["git", "status", "--porcelain"], cwd=tmp_path, capture_output=True, text=True).stdout
    assert status.strip() == "M sections/intro.tex"
    assert "missingkey2020" in (tmp_path / "sections" / "intro.tex").read_text(encoding="utf-8")


def test_check_override_reads_the_message_from_stdin(monkeypatch, capsys):
    import io
    monkeypatch.setattr("sys.stdin", io.StringIO("Fine.\ncommit anyway: deadline at 5pm\n"))
    assert commit_gate.main(["check-override", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == {"override": True, "reason": "deadline at 5pm"}
    monkeypatch.setattr("sys.stdin", io.StringIO("please do not commit anyway: x"))
    assert commit_gate.main(["check-override"]) == 1
    assert capsys.readouterr().out.strip() == "no override phrase"


def test_override_reason_file_round_trips_shell_characters(sample_paper, cfg, monkeypatch, capsys):
    import io
    commit_gate.prepare(sample_paper, cfg, runner=Runner(sample_paper, log="error.log", returncode=2))
    reason = 'it\'s "late"; $HOME `whoami` $(rm -rf x) \\n'
    script = f"python3 {REPO / 'scripts' / 'commit_gate.py'} --root {sample_paper} override --reason-file - " \
             f"<<'PLOMA_REASON'\n{reason}\nPLOMA_REASON\n"
    if shutil.which("bash") is None:
        pytest.skip("bash not installed")
    res = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=60)
    assert res.returncode == 0, res.stderr
    assert gate.load(sample_paper, cfg)["overrides"][-1]["reason"] == reason.strip()
    monkeypatch.setattr("sys.stdin", io.StringIO("   \n"))
    assert commit_gate.main(["--root", str(sample_paper), "override", "--reason-file", "-"]) == 2


def test_override_exit_codes_come_from_the_outcome_type(sample_paper, cfg, monkeypatch):
    def refused(*a, **k):
        raise gate.OverrideRefused("any wording")

    def broken(*a, **k):
        raise ValueError("mentions consecutive and nothing to override")
    monkeypatch.setattr(commit_gate, "override", refused)
    assert commit_gate.main(["--root", str(sample_paper), "override", "--reason", "x"]) == 1
    monkeypatch.setattr(commit_gate, "override", broken)
    assert commit_gate.main(["--root", str(sample_paper), "override", "--reason", "x"]) == 2


def _body() -> str:
    return _skill_text().split("\n---\n", 1)[1]


def test_commit_skill_allowed_tools_are_narrow():
    import _yamlio
    fm = _yamlio.loads_yaml(_skill_text().split("\n---\n", 1)[0].removeprefix("---\n"))
    tools = [s.strip() for s in fm["allowed-tools"].split(",")]
    for needed in ("Bash(gh pr create *)", "Bash(gh repo view *)", "Bash(git push -u origin *)", "Bash(git remote *)"):
        assert needed in tools, needed
    for broad in ("Bash(gh *)", "Bash(git push *)", "Bash(git checkout *)", "Bash", "Bash(git *)"):
        assert broad not in tools, broad


def test_override_is_recorded_right_before_the_commit():
    body = _body()
    record = body.index("override --json --reason-file -")
    assert body.index("## Step 0b: Doctor") < body.index("## Step 1:") < body.index("## Step 4: Commit") < record
    assert record < body.index("git commit -F -")
    assert "git add -- <outputs.dir>/verdicts/commit-gate.json" in body[record:body.index("git commit -F -")]
    step0 = body[body.index("## Step 0: Gate"):body.index("## Step 0b: Doctor")]
    assert not re.search(r"commit_gate\.py\" override", step0) and "Then continue to Step 0b." in step0
    assert "so an attempt that stops earlier does not count" in step0


def test_clean_tree_stops_before_prepare():
    body = _body()
    clean = body.index("git status --porcelain")
    assert clean < body.index("commit_gate.py\" prepare")
    assert "Nothing to commit." in body[clean:body.index("## Step 0: Gate")]


def test_arguments_never_override():
    body = _body()
    assert "never counts as an override" in body and "separate user message" in body
    assert "reference matcher" in body
