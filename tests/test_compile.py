"""compile.py: build runner (stubbed), log triage, pages vs budget, report, gate and state entries."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

import compile as compile_mod
import gate
import pdf_pages
import ploma_config
import state

FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture(autouse=True)
def _no_poppler(monkeypatch):
    """r2d2 has no pdfinfo or pdftotext; make every machine behave the same."""
    monkeypatch.setattr(pdf_pages, "_which", lambda name: None)


class Runner:
    """Stand-in for subprocess.run: records calls, drops a fixture log and PDF into place."""

    def __init__(self, root: Path, log: str | None = "clean.log", pdf: str | None = "three_pages.pdf",
                 returncode: int = 0, stdout: str = "", exc: Exception | None = None):
        self.root, self.log, self.pdf = root, log, pdf
        self.returncode, self.stdout, self.exc = returncode, stdout, exc
        self.calls: list[tuple] = []

    def __call__(self, cmd, **kw):
        self.calls.append((cmd, kw))
        if self.exc is not None:
            raise self.exc
        is_clean = isinstance(cmd, list) and "-c" in cmd
        if not is_clean:
            if self.log:
                shutil.copyfile(FIXTURES / "logs" / self.log, self.root / "main.log")
            if self.pdf:
                shutil.copyfile(FIXTURES / "pdf" / self.pdf, self.root / "main.pdf")
        return subprocess.CompletedProcess(cmd, self.returncode, self.stdout, "")


def _set_cfg(root: Path, old: str, new: str) -> None:
    p = root / "ploma.yaml"
    text = p.read_text(encoding="utf-8")
    assert old in text
    p.write_text(text.replace(old, new), encoding="utf-8")


def test_clean_run_passes_and_records_gate_with_pages(sample_paper, cfg):
    runner = Runner(sample_paper)
    rep = compile_mod.run(sample_paper, cfg, runner=runner)
    assert rep.ok and rep.status == "PASS"
    assert rep.pages == 3 and rep.budget["status"] == "SKIP" and rep.budget["unverified"]
    assert rep.returncode == 0
    cmd, kw = runner.calls[0]
    assert cmd == "make" and kw.get("shell") is True
    assert Path(kw["cwd"]).resolve() == sample_paper.resolve()
    assert kw.get("timeout") == 600
    entry = gate.load(sample_paper, cfg)["checks"]["compile"]
    assert entry["status"] == "PASS" and entry["pages"] == 3
    assert entry["overfull"] == 0 and entry["undefined"] == 0
    assert entry["artifact"] == "quality_reports/compile_main.md"
    last = state.load(sample_paper, cfg)["events"][-1]
    assert last["skill"] == "compile" and last["status"] == "PASS"
    report = (sample_paper / "quality_reports" / "compile_main.md").read_text(encoding="utf-8")
    for heading in ("## Build", "## Errors", "## Undefined", "## Overfull", "## Pages vs budget", "## Next step"):
        assert heading in report
    assert rep.report_path == sample_paper.resolve() / "quality_reports" / "compile_main.md"


def test_error_log_fails_and_report_names_file_and_line(sample_paper, cfg):
    runner = Runner(sample_paper, log="error.log", returncode=2)
    rep = compile_mod.run(sample_paper, cfg, runner=runner)
    assert not rep.ok and rep.status == "FAIL"
    assert rep.log.errors[0]["line"] == 42
    report = rep.report_path.read_text(encoding="utf-8")
    assert "sections/method.tex:42" in report
    assert "fix the first error" in report.lower()
    assert gate.load(sample_paper, cfg)["checks"]["compile"]["status"] == "FAIL"


def test_undefined_citation_fails_and_recommends_validate_bib(sample_paper, cfg):
    rep = compile_mod.run(sample_paper, cfg, runner=Runner(sample_paper, log="undefined.log"))
    assert rep.status == "FAIL"
    assert "smith2020" in rep.log.undefined_citations
    report = rep.report_path.read_text(encoding="utf-8")
    assert "smith2020" in report and "/ploma:validate-bib" in report
    entry = gate.load(sample_paper, cfg)["checks"]["compile"]
    assert entry["undefined"] == len(rep.log.undefined_citations) + len(rep.log.undefined_references) >= 2


def test_over_budget_fails_with_over_by(sample_paper):
    _set_cfg(sample_paper, "page_budget: 8", "page_budget: 2")
    _set_cfg(sample_paper, "page_budget_includes_refs: false", "page_budget_includes_refs: true")
    cfg = ploma_config.load(sample_paper)
    rep = compile_mod.run(sample_paper, cfg, runner=Runner(sample_paper))
    assert rep.status == "FAIL"
    assert rep.budget["status"] == "FAIL" and rep.budget["over_by"] == 1
    report = rep.report_path.read_text(encoding="utf-8")
    assert "/ploma:format" in report and "over by 1" in report


def test_missing_command_uses_latexmk_with_engine_flag(sample_paper):
    _set_cfg(sample_paper, 'command: "make"', "command: null")
    _set_cfg(sample_paper, "engine: pdflatex", "engine: xelatex")
    cfg = ploma_config.load(sample_paper)
    runner = Runner(sample_paper)
    rep = compile_mod.run(sample_paper, cfg, runner=runner)
    cmd, kw = runner.calls[0]
    assert cmd[0] == "latexmk" and "-pdfxe" in cmd and cmd[-1] == "main.tex"
    assert "-interaction=nonstopmode" in cmd and "-halt-on-error" in cmd and "-file-line-error" in cmd
    assert not kw.get("shell")
    assert rep.status == "PASS"


def test_clean_with_make_forces_rebuild_with_dash_b(sample_paper, cfg):
    """R92: make builds are cleaned by forcing the rebuild (make -B), not by make clean."""
    runner = Runner(sample_paper)
    rep = compile_mod.run(sample_paper, cfg, runner=runner, clean=True)
    assert [c[0] for c in runner.calls] == ["make -B"]
    assert rep.command == "make -B" and rep.status == "PASS"


def test_clean_inserts_dash_b_after_make_keeping_the_target(sample_paper):
    _set_cfg(sample_paper, 'command: "make"', 'command: "make pdf"')
    cfg = ploma_config.load(sample_paper)
    runner = Runner(sample_paper)
    compile_mod.run(sample_paper, cfg, runner=runner, clean=True)
    assert [c[0] for c in runner.calls] == ["make -B pdf"]


def test_clean_with_non_make_command_keeps_latexmk_c(sample_paper):
    _set_cfg(sample_paper, 'command: "make"', 'command: "makeindex x && latexmk -pdf main"')
    cfg = ploma_config.load(sample_paper)
    runner = Runner(sample_paper)
    compile_mod.run(sample_paper, cfg, runner=runner, clean=True)
    assert runner.calls[0][0] == ["latexmk", "-c", "main.tex"]
    assert runner.calls[1][0] == "makeindex x && latexmk -pdf main"


def test_clean_without_make_uses_latexmk_c(sample_paper):
    _set_cfg(sample_paper, 'command: "make"', "command: null")
    cfg = ploma_config.load(sample_paper)
    runner = Runner(sample_paper)
    compile_mod.run(sample_paper, cfg, runner=runner, clean=True)
    assert runner.calls[0][0] == ["latexmk", "-c", "main.tex"]
    assert runner.calls[1][0][0] == "latexmk"


def test_build_tool_not_found_is_fail_without_traceback(sample_paper):
    _set_cfg(sample_paper, 'command: "make"', "command: null")
    cfg = ploma_config.load(sample_paper)
    rep = compile_mod.run(sample_paper, cfg, runner=Runner(sample_paper, exc=FileNotFoundError("latexmk")))
    assert rep.status == "FAIL"
    text = rep.report_path.read_text(encoding="utf-8")
    assert "build tool not found: latexmk" in text and "Traceback" not in text


def test_shell_exit_127_is_tool_not_found(sample_paper, cfg):
    rep = compile_mod.run(sample_paper, cfg, runner=Runner(sample_paper, log=None, pdf=None, returncode=127,
                                                           stdout="sh: 1: make: not found\n"))
    assert rep.status == "FAIL"
    assert "build tool not found: make" in rep.report_path.read_text(encoding="utf-8")


def test_missing_log_is_reported_not_a_crash(sample_paper, cfg):
    rep = compile_mod.run(sample_paper, cfg, runner=Runner(sample_paper, log=None))
    assert rep.status == "FAIL"
    assert "log not found" in rep.report_path.read_text(encoding="utf-8")


def test_rerun_alone_is_a_warn_line_and_passes(sample_paper, cfg):
    rep = compile_mod.run(sample_paper, cfg, runner=Runner(sample_paper, log="rerun.log"))
    assert rep.log.rerun_needed
    assert rep.status == "PASS"
    assert "WARN" in rep.report_path.read_text(encoding="utf-8")


def test_output_tail_is_last_40_lines(sample_paper, cfg):
    out = "".join(f"line {i}\n" for i in range(100))
    rep = compile_mod.run(sample_paper, cfg, runner=Runner(sample_paper, stdout=out))
    assert rep.output_tail.splitlines() == [f"line {i}" for i in range(60, 100)]
    assert "line 99" in rep.report_path.read_text(encoding="utf-8")


def test_timeout_is_fail(sample_paper, cfg):
    rep = compile_mod.run(sample_paper, cfg,
                          runner=Runner(sample_paper, exc=subprocess.TimeoutExpired("make", 600)))
    assert rep.status == "FAIL" and "timed out" in rep.report_path.read_text(encoding="utf-8")


def test_to_dict_is_json(sample_paper, cfg):
    rep = compile_mod.run(sample_paper, cfg, runner=Runner(sample_paper))
    d = json.loads(json.dumps(rep.to_dict()))
    assert d["ok"] is True and d["pages"] == 3 and d["log"]["errors"] == []


def test_cli_exit_codes(sample_paper, monkeypatch, capsys):
    monkeypatch.setattr(compile_mod, "_default_runner", Runner(sample_paper))
    assert compile_mod.main(["--root", str(sample_paper), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "PASS"
    monkeypatch.setattr(compile_mod, "_default_runner", Runner(sample_paper, log="error.log", returncode=1))
    assert compile_mod.main(["--root", str(sample_paper)]) == 1
    assert compile_mod.main(["--root", str(sample_paper / "nope")]) == 2


def test_make_reporting_a_missing_compiler_names_it(sample_paper, cfg):
    out = ("pdflatex -interaction=nonstopmode -file-line-error main\n"
           "make: pdflatex: No such file or directory\nmake: *** [Makefile:10: main.pdf] Error 127\n")
    rep = compile_mod.run(sample_paper, cfg, runner=Runner(sample_paper, log=None, pdf=None, returncode=2, stdout=out))
    assert rep.status == "FAIL" and rep.build_error == "build tool not found: pdflatex"
    text = rep.report_path.read_text(encoding="utf-8")
    assert "log not found at main.log" in text and "PDF not found at main.pdf" in text
    assert str(sample_paper) not in text


def test_budget_excludes_references_when_pdftotext_finds_them(sample_paper, monkeypatch):
    _set_cfg(sample_paper, "page_budget: 8", "page_budget: 2")
    cfg = ploma_config.load(sample_paper)
    monkeypatch.setattr(pdf_pages, "_which", lambda n: "/usr/bin/" + n if n == "pdftotext" else None)
    pages_text = "Intro text with references [1].\f2 Method\nmore\n\nReferences\n1. A. Author\f2. B. Author\n"
    monkeypatch.setattr(pdf_pages, "_run", lambda cmd: pages_text)
    rep = compile_mod.run(sample_paper, cfg, runner=Runner(sample_paper))
    assert rep.pages == 3 and rep.budget["pages"] == 2 and rep.budget["status"] == "PASS"
    assert rep.status == "PASS"


def test_budget_unverified_when_references_cannot_be_located(sample_paper):
    """R83: pdftotext absent, budget excludes references, total over budget: PASS, budget unverified."""
    _set_cfg(sample_paper, "page_budget: 8", "page_budget: 2")
    cfg = ploma_config.load(sample_paper)
    rep = compile_mod.run(sample_paper, cfg, runner=Runner(sample_paper))
    assert rep.status == "PASS" and rep.pages == 3
    assert rep.budget["unverified"] is True and rep.budget["status"] == "SKIP"
    text = rep.report_path.read_text(encoding="utf-8")
    assert "3 pages in total; page budget could not be checked: " in text and "pdftotext not found" in text
    assert gate.load(sample_paper, cfg)["checks"]["compile"]["budget_unverified"] is True
    assert state.load(sample_paper, cfg)["events"][-1]["budget_unverified"] is True


def test_budget_located_has_no_unverified_flag(sample_paper, cfg):
    _set_cfg(sample_paper, "page_budget_includes_refs: false", "page_budget_includes_refs: true")
    cfg = ploma_config.load(sample_paper)
    compile_mod.run(sample_paper, cfg, runner=Runner(sample_paper))
    assert "budget_unverified" not in gate.load(sample_paper, cfg)["checks"]["compile"]


def _age(paths, seconds_ago):
    import os
    import time
    t = time.time() - seconds_ago
    for p in paths:
        os.utime(p, (t, t))


def _sources(root: Path) -> list[Path]:
    return [p for p in root.rglob("*") if p.suffix in (".tex", ".bib")]


def test_up_to_date_build_passes_on_the_existing_log(sample_paper, cfg):
    """R92: exit 0, log not rewritten, log and PDF newer than every source: PASS, up to date."""
    shutil.copyfile(FIXTURES / "logs" / "clean.log", sample_paper / "main.log")
    shutil.copyfile(FIXTURES / "pdf" / "three_pages.pdf", sample_paper / "main.pdf")
    _age(_sources(sample_paper), 1000)
    _age([sample_paper / "main.log", sample_paper / "main.pdf"], 100)
    rep = compile_mod.run(sample_paper, cfg, runner=Runner(sample_paper, log=None, pdf=None,
                                                           stdout="make: Nothing to be done for 'build'.\n"))
    assert rep.status == "PASS", rep.reasons
    assert "build was up to date" in rep.notes
    assert rep.pages == 3
    assert "build was up to date" in rep.report_path.read_text(encoding="utf-8")


def test_up_to_date_build_still_reports_errors_in_the_existing_log(sample_paper, cfg):
    shutil.copyfile(FIXTURES / "logs" / "undefined.log", sample_paper / "main.log")
    shutil.copyfile(FIXTURES / "pdf" / "three_pages.pdf", sample_paper / "main.pdf")
    _age(_sources(sample_paper), 1000)
    _age([sample_paper / "main.log", sample_paper / "main.pdf"], 100)
    rep = compile_mod.run(sample_paper, cfg, runner=Runner(sample_paper, log=None, pdf=None))
    assert rep.status == "FAIL" and rep.log.undefined_citations


def test_stale_log_older_than_a_source_fails_with_clean_advice(sample_paper, cfg):
    """R92 (supersedes R88): exit 0 but a source is newer than the log: make did not rebuild."""
    log = sample_paper / "main.log"
    shutil.copyfile(FIXTURES / "logs" / "clean.log", log)
    shutil.copyfile(FIXTURES / "pdf" / "three_pages.pdf", sample_paper / "main.pdf")
    _age([log, sample_paper / "main.pdf"], 1000)
    _age([sample_paper / "main.tex"], 100)
    rep = compile_mod.run(sample_paper, cfg, runner=Runner(sample_paper, log=None, pdf=None))
    assert rep.status == "FAIL"
    assert "make did not rebuild; run /ploma:compile --clean" in rep.report_path.read_text(encoding="utf-8")


def test_old_log_after_a_failed_build_is_not_written_by_this_build(sample_paper, cfg):
    log = sample_paper / "main.log"
    shutil.copyfile(FIXTURES / "logs" / "clean.log", log)
    _age([log], 1000)
    rep = compile_mod.run(sample_paper, cfg, runner=Runner(sample_paper, log=None, returncode=2))
    assert rep.status == "FAIL"
    assert "log was not written by this build: main.log" in rep.report_path.read_text(encoding="utf-8")


FAKE_PDFLATEX = """#!/bin/sh
for a in "$@"; do last="$a"; done
stem="${last%.tex}"
cp "__FIX__/logs/clean.log" "$stem.log"
cp "__FIX__/pdf/three_pages.pdf" "$stem.pdf"
echo "Output written on $stem.pdf"
"""
FAKE_BIBTEX = """#!/bin/sh
touch "$1.bbl"
"""


@pytest.mark.skipif(shutil.which("make") is None, reason="make not installed")
def test_real_make_up_to_date_then_clean_forces_rebuild(sample_paper, cfg, tmp_path, monkeypatch):
    """R92 with REAL make and a fake engine: build, build again (up to date), then --clean (make -B)."""
    import os
    fakebin = tmp_path / "fakebin"
    fakebin.mkdir()
    for name, body in (("pdflatex", FAKE_PDFLATEX.replace("__FIX__", str(FIXTURES))), ("bibtex", FAKE_BIBTEX)):
        (fakebin / name).write_text(body, encoding="utf-8")
        (fakebin / name).chmod(0o755)
    monkeypatch.setenv("PATH", f"{fakebin}{os.pathsep}{os.environ.get('PATH', '')}")
    _age([p for p in sample_paper.rglob("*") if p.is_file()], 1000)

    first = compile_mod.run(sample_paper, cfg)
    assert first.status == "PASS", (first.reasons, first.output_tail)
    _age([sample_paper / "main.log", sample_paper / "main.pdf"], 100)
    log_mtime = (sample_paper / "main.log").stat().st_mtime

    second = compile_mod.run(sample_paper, cfg)
    assert "Nothing to be done" in second.output_tail or "up to date" in second.output_tail
    assert (sample_paper / "main.log").stat().st_mtime == log_mtime, "make rebuilt; the test needs an up-to-date target"
    assert second.status == "PASS", second.reasons
    assert "build was up to date" in second.notes

    third = compile_mod.run(sample_paper, cfg, clean=True)
    assert third.command == "make -B"
    assert third.status == "PASS", third.reasons
    assert (sample_paper / "main.log").stat().st_mtime > log_mtime
    assert "build was up to date" not in third.notes


def test_default_runner_kills_the_process_group_on_timeout(tmp_path):
    """Grandchildren (pdflatex under make) must not outlive a timed-out build."""
    import os
    import time
    pidfile = tmp_path / "child.pid"
    cmd = f"sleep 30 & echo $! > {pidfile}; wait"
    started = time.time()
    with pytest.raises(subprocess.TimeoutExpired):
        compile_mod._group_runner(cmd, cwd=str(tmp_path), shell=True, capture_output=True, text=True, timeout=1)
    assert time.time() - started < 10, "the runner waited for the orphaned child instead of killing it"
    pid = int(pidfile.read_text().strip())
    deadline = time.time() + 5
    while time.time() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            break
        time.sleep(0.05)
    else:
        os.kill(pid, 9)
        pytest.fail("background child survived the timeout")


def test_default_runner_returns_completed_process(tmp_path):
    res = compile_mod._group_runner("echo hi; exit 3", cwd=str(tmp_path), shell=True, timeout=10)
    assert res.returncode == 3 and res.stdout == "hi\n"


def test_classic_error_without_an_opened_file_is_attributed_to_the_main_file(sample_paper, cfg):
    rep = compile_mod.run(sample_paper, cfg, runner=Runner(sample_paper, log="classic_no_file.log", returncode=1))
    text = rep.report_path.read_text(encoding="utf-8")
    assert "`main.tex:3`" in text and "?:" not in text and "`?" not in text
    assert "first at main.tex:3" in rep.reasons[-1] or any("main.tex:3" in r for r in rep.reasons)


def test_halt_on_error_log_counts_one_error(sample_paper, cfg):
    rep = compile_mod.run(sample_paper, cfg, runner=Runner(sample_paper, log="halt_classic.log", returncode=1))
    assert len(rep.log.errors) == 1
    assert "1 error(s) in the log, first at sections/method.tex:9" in rep.reasons
