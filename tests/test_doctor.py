"""Doctor readiness audit (spec section 9)."""
from __future__ import annotations

import json
import os
import shutil

import doctor
import host
from _findings import FAIL, INFO, PASS, SKIP, WARN

GROUP_IDS = ["runtime", "config", "toolchain", "manuscript", "host", "project-files", "state", "dependencies",
             "legacy-harness"]
PRESENT = ("pdflatex", "bibtex", "pdfinfo", "pdftotext", "make", "git")


def _which(present=PRESENT):
    return lambda n: "/usr/bin/" + n if n in present else None


def _run(root, which=None, **kw):
    return doctor.run(root, which=which or _which(), home=root / "nohome", **kw)


def _all(r):
    return [f for g in r.groups for f in g["findings"]]


def _by_id(r, fid):
    return next(f for f in _all(r) if f.id == fid)


def _snapshot(root):
    return {str(p.relative_to(root)): (p.stat().st_mtime_ns, p.read_bytes() if p.is_file() else None)
            for p in sorted(root.rglob("*"))}


def _set_cfg(root, old, new):
    p = root / "ploma.yaml"
    text = p.read_text(encoding="utf-8")
    assert old in text
    p.write_text(text.replace(old, new), encoding="utf-8")


def test_empty_dir_is_not_ready(tmp_path):
    r = doctor.run(tmp_path, which=lambda n: None, home=tmp_path / "nohome")
    assert r.verdict == "NOT_READY"
    first_fail = next(f for g in r.groups for f in g["findings"] if f.status == FAIL)
    assert first_fail.id == "config.missing" and "/ploma:onboard" in first_fail.remediation


def test_empty_dir_skips_groups_needing_config(tmp_path):
    r = doctor.run(tmp_path, which=_which(), home=tmp_path / "nohome")
    assert [g["id"] for g in r.groups] == GROUP_IDS
    for g in r.groups:
        if g["id"] == "host":
            assert [(f.id, f.status) for f in g["findings"]] == [("host.running", INFO), ("host.skipped", SKIP)]
        if g["id"] in ("toolchain", "manuscript", "project-files", "state", "legacy-harness"):
            assert [f.status for f in g["findings"]] == [SKIP], g
            assert g["findings"][0].summary == "no ploma.yaml" or "no ploma.yaml" in g["findings"][0].observed
    assert [f.id for f in _all(r) if f.status == FAIL] == ["config.missing"]
    assert any(f.id.startswith("runtime.") for f in _all(r))
    assert any(f.id == "dependencies.superpowers" for f in _all(r))


def test_onboarded_sample_is_ready(onboarded_sample, repo_root):
    host.ensure_plugin_link(onboarded_sample, repo_root)
    r = _run(onboarded_sample)
    assert r.verdict == "READY", r.render()
    assert [g["id"] for g in r.groups] == GROUP_IDS
    for f in _all(r):
        assert f.id.split(".")[0] == f.group, f


def test_missing_linters_are_skip_not_warn(onboarded_sample, repo_root):
    host.ensure_plugin_link(onboarded_sample, repo_root)
    r = _run(onboarded_sample, which=lambda n: None if n in ("chktex", "lacheck", "texcount") else "/usr/bin/" + n)
    linters = [f for f in _all(r) if f.id in ("toolchain.chktex", "toolchain.lacheck", "toolchain.texcount")]
    assert len(linters) == 3 and all(f.status == SKIP for f in linters)
    assert all(f.summary == "optional linter not installed" or "optional linter not installed" in f.observed
               for f in linters)
    assert r.verdict == "READY", r.render()


def test_present_linters_pass(onboarded_sample):
    r = _run(onboarded_sample, which=lambda n: "/usr/bin/" + n)
    assert _by_id(r, "toolchain.chktex").status == PASS


def test_missing_engine_and_bib_tool_fail(onboarded_sample):
    r = _run(onboarded_sample, which=_which(("pdfinfo", "pdftotext", "make", "git")))
    assert _by_id(r, "toolchain.engine").status == FAIL
    assert _by_id(r, "toolchain.bib_tool").status == FAIL
    assert r.verdict == "NOT_READY"


def test_engine_follows_config(onboarded_sample):
    _set_cfg(onboarded_sample, "engine: pdflatex", "engine: xelatex")
    r = _run(onboarded_sample)
    f = _by_id(r, "toolchain.engine")
    assert f.status == FAIL and "xelatex" in f.summary + f.observed


def test_missing_make_fails_when_command_uses_it(onboarded_sample):
    r = _run(onboarded_sample, which=_which(("pdflatex", "bibtex", "pdfinfo", "pdftotext", "git")))
    assert _by_id(r, "toolchain.make").status == FAIL


def test_null_command_needs_latexmk(onboarded_sample):
    _set_cfg(onboarded_sample, 'command: "make"', "command: null")
    r = _run(onboarded_sample)
    assert _by_id(r, "toolchain.latexmk").status == FAIL
    assert not any(f.id == "toolchain.make" for f in _all(r))
    r = _run(onboarded_sample, which=_which(PRESENT + ("latexmk",)))
    assert _by_id(r, "toolchain.latexmk").status == PASS


def test_missing_pdf_tools_warn(onboarded_sample):
    r = _run(onboarded_sample, which=_which(("pdflatex", "bibtex", "make", "git")))
    assert _by_id(r, "toolchain.pdfinfo").status == WARN
    assert _by_id(r, "toolchain.pdftotext").status == WARN
    assert r.verdict == "READY_WITH_WARNINGS"


def test_build_dry_run_is_skip(onboarded_sample):
    f = _by_id(_run(onboarded_sample), "toolchain.build_dry_run")
    assert f.status == SKIP and "not run by doctor" in f.summary + f.observed


def test_runtime_group(onboarded_sample):
    r = _run(onboarded_sample)
    assert _by_id(r, "runtime.python").status == PASS
    loader = _by_id(r, "runtime.yaml_loader")
    assert loader.status == INFO and ("pyyaml" in loader.summary or "yamlmini" in loader.summary)
    assert _by_id(r, "runtime.git").status == PASS
    r = _run(onboarded_sample, which=_which(("pdflatex", "bibtex", "pdfinfo", "pdftotext", "make")))
    assert _by_id(r, "runtime.git").status == WARN


def test_stale_pdf_warns(onboarded_sample):
    pdf = onboarded_sample / "main.pdf"
    old = pdf.stat().st_mtime - 3600
    os.utime(pdf, (old, old))
    r = _run(onboarded_sample)
    f = _by_id(r, "manuscript.pdf_stale")
    assert f.status == WARN and f.remediation == "Run /ploma:compile"
    assert r.verdict == "READY_WITH_WARNINGS"


def test_missing_pdf_warns(onboarded_sample):
    (onboarded_sample / "main.pdf").unlink()
    f = _by_id(_run(onboarded_sample), "manuscript.pdf_stale")
    assert f.status == WARN and f.remediation == "Run /ploma:compile"


def test_proposal_type_is_not_ready(onboarded_sample):
    _set_cfg(onboarded_sample, "type: paper", "type: proposal")
    r = _run(onboarded_sample)
    assert r.verdict == "NOT_READY"
    assert _by_id(r, "config.document_type_unsupported").status == FAIL


def test_config_parse_error(onboarded_sample):
    (onboarded_sample / "ploma.yaml").write_text("document: [unclosed\n", encoding="utf-8")
    r = _run(onboarded_sample)
    f = _by_id(r, "config.parse")
    assert f.status == FAIL and f.observed
    assert r.verdict == "NOT_READY"


def test_unknown_venue_fails(onboarded_sample):
    _set_cfg(onboarded_sample, "profile: generic-conference", "profile: no-such-venue")
    f = _by_id(_run(onboarded_sample), "config.venue")
    assert f.status == FAIL and "no-such-venue" in f.observed


def test_malformed_venue_override_surfaces(onboarded_sample):
    d = onboarded_sample / "ploma.d" / "venues"
    d.mkdir(parents=True)
    (d / "generic-conference.yaml").write_text("key: generic-conference\nkind: banquet\n", encoding="utf-8")
    r = _run(onboarded_sample)
    fails = [f for f in _all(r) if f.group == "config" and f.status == FAIL]
    assert any(f.id.startswith("config.venue.") for f in fails), r.render()
    assert r.verdict == "NOT_READY"


def test_unknown_discipline_fails(onboarded_sample):
    _set_cfg(onboarded_sample, "  anonymized: true", "  anonymized: true\n  discipline: no-such-field")
    f = _by_id(_run(onboarded_sample), "config.discipline")
    assert f.status == FAIL and "no-such-field" in f.observed


def test_bib_findings_aggregate(onboarded_sample):
    sec = onboarded_sample / "sections" / "intro.tex"
    sec.write_text(sec.read_text(encoding="utf-8") + "\n\\cite{NoSuchKey2020}\n", encoding="utf-8")
    pdf = onboarded_sample / "main.pdf"
    os.utime(pdf, (pdf.stat().st_mtime + 3600,) * 2)
    r = _run(onboarded_sample)
    bib = [f for f in _all(r) if f.id.startswith("manuscript.bib")]
    fails = [f for f in bib if f.status == FAIL]
    assert len(fails) == 1 and "NoSuchKey2020" in fails[0].observed
    assert sum(f.status == INFO for f in bib) == 1


def test_figure_provenance_info_then_warn_when_required(onboarded_sample):
    m = onboarded_sample / "sections" / "method.tex"
    m.write_text(m.read_text(encoding="utf-8").replace("% ploma:source", "% source"), encoding="utf-8")
    pdf = onboarded_sample / "main.pdf"
    os.utime(pdf, (pdf.stat().st_mtime + 3600,) * 2)
    f = _by_id(_run(onboarded_sample), "manuscript.figure_provenance")
    assert f.status == INFO and "figures/fig1.pdf" in f.observed
    _set_cfg(onboarded_sample, "  outputs_dir: results", "  outputs_dir: results\n  figure_provenance: required")
    f = _by_id(_run(onboarded_sample), "manuscript.figure_provenance")
    assert f.status == WARN


def test_figure_provenance_only_with_pipeline(onboarded_sample):
    _set_cfg(onboarded_sample, "enabled: true", "enabled: false")
    assert not any(f.id == "manuscript.figure_provenance" for f in _all(_run(onboarded_sample)))


def test_project_files_pass_and_receipt_info_without_receipt(onboarded_sample):
    r = _run(onboarded_sample)
    for check in ("rules", "instructions_section", "gitignore", "receipt"):
        assert _by_id(r, f"project-files.{check}").status == PASS, check
    (onboarded_sample / "quality_reports" / "ploma-receipt.json").unlink()
    assert _by_id(_run(onboarded_sample), "project-files.receipt").status == INFO


def test_state_group(onboarded_sample):
    r = _run(onboarded_sample)
    gate = _by_id(r, "state.gate")
    assert gate.status == INFO and "INCOMPLETE" in gate.summary + gate.observed
    stage = _by_id(r, "state.next_stage")
    assert stage.status == INFO and "compile" in stage.summary
    out = onboarded_sample / "quality_reports" / "verdicts"
    out.mkdir(parents=True)
    (out / "commit-gate.json").write_text(json.dumps({"checks": {}, "overrides": [], "override_streak": 2}),
                                          encoding="utf-8")
    r = _run(onboarded_sample)
    assert _by_id(r, "state.override_streak").status == WARN


def test_superpowers_missing_warns(onboarded_sample):
    (onboarded_sample / ".claude" / "settings.json").unlink()
    r = _run(onboarded_sample)
    f = _by_id(r, "dependencies.superpowers")
    assert f.status == WARN
    assert "/plugin install superpowers@claude-plugins-official" in f.remediation
    assert "superpowers-marketplace" in f.remediation
    assert r.verdict == "READY_WITH_WARNINGS"


def test_citation_apis_skip(onboarded_sample):
    f = _by_id(_run(onboarded_sample), "dependencies.citation_apis")
    assert f.status == SKIP and "doctor makes no network calls" in f.summary + f.observed


def test_legacy_harness_conflict_warns(onboarded_sample):
    (onboarded_sample / ".claude" / "scripts").mkdir()
    (onboarded_sample / ".claude" / "scripts" / "statusline.sh").write_text("#!/bin/sh\n", encoding="utf-8")
    r = _run(onboarded_sample)
    warns = [f for f in _all(r) if f.group == "legacy-harness" and f.status == WARN]
    assert len(warns) == 1
    assert "status line" in warns[0].summary
    assert warns[0].remediation == "retire it (see the onboard retirement checklist)"


def test_legacy_harness_clean_passes(onboarded_sample):
    g = next(g for g in _run(onboarded_sample).groups if g["id"] == "legacy-harness")
    assert [f.status for f in g["findings"]] == [PASS]


def test_render_format(onboarded_sample):
    r = _run(onboarded_sample)
    txt = r.render()
    lines = txt.splitlines()
    assert lines[0] == f"Overall verdict: {r.verdict}"
    c = r.counts
    assert lines[1] == f"Counts: PASS {c['PASS']} WARN {c['WARN']} FAIL {c['FAIL']} INFO {c['INFO']} SKIP {c['SKIP']}"
    assert "1. Runtime" in lines and "9. Legacy harness" in lines
    assert any(line.startswith("- PASS runtime.python: ") for line in lines)
    empty = onboarded_sample.parent / "empty"
    empty.mkdir()
    elines = _run(empty).render().splitlines()
    i = elines.index("- FAIL config.missing: " + _by_id(_run(empty), "config.missing").summary)
    assert elines[i + 1].startswith("  Observed: ") and elines[i + 2] == "  Remediation: Run /ploma:onboard"
    assert sum(c.values()) == len(_all(r))


def test_render_default_which(onboarded_sample):
    txt = doctor.run(onboarded_sample).render()
    assert txt.startswith("Overall verdict: ") and "Counts:" in txt.splitlines()[1]


def test_verdict_ladder_ignores_info_and_skip():
    from _findings import Finding
    assert doctor.verdict_for([Finding("a.b", INFO, "x"), Finding("a.c", SKIP, "y")]) == "READY"
    assert doctor.verdict_for([Finding("a.b", WARN, "x")]) == "READY_WITH_WARNINGS"
    assert doctor.verdict_for([Finding("a.b", WARN, "x"), Finding("a.c", FAIL, "y")]) == "NOT_READY"


def test_doctor_writes_nothing(onboarded_sample, tmp_path):
    before = _snapshot(onboarded_sample)
    _run(onboarded_sample)
    doctor.main([str(onboarded_sample), "--json"])
    assert _snapshot(onboarded_sample) == before
    empty = tmp_path / "empty"
    empty.mkdir()
    doctor.run(empty, which=lambda n: None, home=empty / "nohome")
    assert list(empty.iterdir()) == []


def test_cli_json_and_exit_codes(onboarded_sample, tmp_path, capsys):
    empty = tmp_path / "empty"
    empty.mkdir()
    assert doctor.main([str(empty), "--json"]) == 1
    data = json.loads(capsys.readouterr().out)
    assert data["verdict"] == "NOT_READY" and [g["id"] for g in data["groups"]] == GROUP_IDS
    assert data["groups"][1]["findings"][0]["id"] == "config.missing"
    assert doctor.main([str(tmp_path / "nope")]) == 2
    capsys.readouterr()
    code = doctor.main([str(onboarded_sample)])
    out = capsys.readouterr().out
    assert out.startswith("Overall verdict: ")
    assert code == (1 if "NOT_READY" in out.splitlines()[0] else 0)


def test_gate_fail_warns_and_incomplete_stays_info(onboarded_sample):
    import gate
    import ploma_config
    cfg = ploma_config.load(onboarded_sample)
    assert _by_id(_run(onboarded_sample), "state.gate").status == INFO
    sha = gate.manuscript_sha(onboarded_sample, cfg)
    out = onboarded_sample / "quality_reports" / "verdicts"
    out.mkdir(parents=True)
    entry = {"at": "2026-10-29T00:00:00Z", "artifact": "x", "manuscript_sha": sha}
    (out / "commit-gate.json").write_text(json.dumps({
        "checks": {"compile": dict(entry, status="FAIL"), "bib": dict(entry, status="PASS")},
        "overrides": [], "override_streak": 0}), encoding="utf-8")
    r = _run(onboarded_sample)
    f = _by_id(r, "state.gate")
    assert f.status == WARN and "compile" in f.summary
    assert f.remediation == "fix the failing check and re-run it (e.g. /ploma:compile, /ploma:validate-bib)"
    assert r.verdict == "READY_WITH_WARNINGS", r.render()


def test_gate_error_keeps_other_state_findings(onboarded_sample, monkeypatch):
    import gate

    def boom(root, cfg):
        raise OSError("cannot read sections/x.tex")
    monkeypatch.setattr(gate, "manuscript_sha", boom)
    r = _run(onboarded_sample)
    f = _by_id(r, "state.gate")
    assert f.status == WARN and "cannot read sections/x.tex" in f.observed
    assert _by_id(r, "state.override_streak").status == PASS
    assert _by_id(r, "state.next_stage").status == INFO


def test_crash_in_blocking_groups_is_fail(onboarded_sample, monkeypatch):
    def boom(*a, **k):
        raise TypeError("unexpected shape")
    for target, attr, group in ((doctor.ploma_config, "validate", "config"), (doctor, "_uses", "toolchain"),
                                (doctor.bib_check, "check", "manuscript")):
        with monkeypatch.context() as m:
            m.setattr(target, attr, boom)
            r = _run(onboarded_sample)
            f = _by_id(r, f"{group}.error")
            assert f.status == FAIL and f.observed == "TypeError: unexpected shape"
            assert r.verdict == "NOT_READY"


def test_crash_in_other_groups_is_warn(onboarded_sample, monkeypatch):
    def boom(*a, **k):
        raise TypeError("unexpected shape")
    monkeypatch.setattr(doctor.inventory, "detect_legacy_harness", boom)
    f = _by_id(_run(onboarded_sample), "legacy-harness.error")
    assert f.status == WARN


def test_missing_document_root_skips_pdf_freshness(onboarded_sample):
    _set_cfg(onboarded_sample, 'root: "."', 'root: "paper"')
    r = _run(onboarded_sample)
    f = _by_id(r, "manuscript.pdf_fresh")
    assert f.status == SKIP and f.summary == "document.root missing"


def test_legacy_harness_grouped_one_warn_per_kind(onboarded_sample, monkeypatch):
    """R127 D5: one WARN per legacy kind, the count in the summary, paths one per line in Observed (25 then "and N more")."""
    found = [{"kind": "rule_restates_facts", "path": f".claude/rules/r{i:02d}.md",
              "consequence": "rule restates build facts that ploma.yaml now owns"} for i in range(28)]
    found += [{"kind": "skill_name_conflict", "path": ".claude/skills/compile",
               "consequence": "duplicate skill name: /compile would shadow or confuse /ploma:compile"},
              {"kind": "skill_name_conflict", "path": ".claude/skills/doctor",
               "consequence": "duplicate skill name: /doctor would shadow or confuse /ploma:doctor"},
              {"kind": "statusline", "path": ".claude/scripts/statusline.sh",
               "consequence": "legacy status line replaces the one that shows ploma's lifecycle stage"}]
    monkeypatch.setattr(doctor.inventory, "detect_legacy_harness", lambda root: found)
    r = _run(onboarded_sample)
    g = next(g for g in r.groups if g["id"] == "legacy-harness")
    assert [f.id for f in g["findings"]] == ["legacy-harness.skill_name_conflict", "legacy-harness.statusline",
                                             "legacy-harness.rule_restates_facts"]
    rules = g["findings"][2]
    assert rules.status == WARN and "28" in rules.summary
    lines = rules.observed.splitlines()
    assert lines[:25] == [f".claude/rules/r{i:02d}.md" for i in range(25)] and lines[25] == "and 3 more"
    skills = g["findings"][0]
    assert "2" in skills.summary and skills.observed.splitlines() == [".claude/skills/compile", ".claude/skills/doctor"]
    text = r.render()
    assert "\n  Observed: .claude/rules/r00.md\n    .claude/rules/r01.md\n" in text
    assert sum(1 for line in text.splitlines() if line.startswith("- WARN legacy-harness.")) == 3


# ---------------------------------------------------------------- host group (multi-host spec section 12)

def _codex_root(onboarded_for, monkeypatch):
    root = onboarded_for("codex")
    monkeypatch.setenv("PLOMA_HOST", "codex")
    return root


def test_running_is_reported_without_config(tmp_path, monkeypatch):
    monkeypatch.setenv("PLOMA_HOST", "codex")
    f = _by_id(doctor.run(tmp_path, which=_which(), home=tmp_path / "nohome"), "host.running")
    assert f.status == INFO and f.summary == "running under Codex"


def test_host_mismatch_is_first_and_not_ready(onboarded_sample, monkeypatch):
    monkeypatch.setenv("PLOMA_HOST", "codex")
    r = _run(onboarded_sample)
    first = _all(r)[0]
    assert r.verdict == "NOT_READY" and first.id == "host.host_mismatch" and first.status == FAIL
    assert first.summary == "repo is onboarded for Claude Code; you are running Codex"
    assert first.remediation == "Run /ploma:onboard to switch."
    lines = r.render().splitlines()
    i = lines.index(f"- FAIL host.host_mismatch: {first.summary}")
    assert lines[i + 1] == "  Observed: receipt host: claude"
    assert lines[i + 2] == "  Remediation: Run $ploma:onboard to switch."
    ids = {f.id for f in _all(r)}
    assert "host.running" in ids and "host.other_host_files" not in ids  # nothing but Claude files on disk
    assert not any(i.startswith(("project-files.drift", "project-files.missing", "project-files.instructions_section"))
                   for i in ids), ids


def test_host_match_and_other_host_files_info(onboarded_for, monkeypatch):
    r = _run(_codex_root(onboarded_for, monkeypatch))
    match = _by_id(r, "host.host_match")
    assert match.status == PASS and match.summary == "running under Codex; repo onboarded for Codex"
    other = _by_id(r, "host.other_host_files")
    assert other.status == INFO and "CLAUDE.md" in other.observed
    assert ".claude/rules/ploma-manuscript.md" in other.observed
    assert "AGENTS.md" not in other.observed


def test_unknown_host_runs_with_claude_paths(onboarded_sample):
    (onboarded_sample / ".ploma" / "host.json").unlink()  # apply records the host; a plain shell has none
    r = _run(onboarded_sample)
    assert _by_id(r, "host.host_unknown").status == INFO
    assert _by_id(r, "host.host_match").status == PASS
    assert _by_id(r, "project-files.instructions_section").status == PASS
    assert not any(f.id.startswith("host.root_export") for f in _all(r))


def test_root_export_and_link_warnings(onboarded_for, monkeypatch):
    root = _codex_root(onboarded_for, monkeypatch)
    (root / ".codex" / "config.toml").unlink()
    shutil.rmtree(root / ".ploma", ignore_errors=True)
    r = _run(root)
    missing = _by_id(r, "host.root_export_missing")
    assert missing.status == WARN and ".codex/config.toml" in missing.remediation
    link = _by_id(r, "host.plugin_link")
    assert link.status == WARN
    assert link.remediation == ("Start a new session (the session hook refreshes .ploma/plugin), "
                                "or run /ploma:onboard.")


def test_dangling_plugin_link_warns_on_claude(onboarded_sample, monkeypatch, tmp_path):
    monkeypatch.setenv("PLOMA_HOST", "claude")
    import shutil
    gone = tmp_path / "gone"
    (gone / "scripts").mkdir(parents=True)
    (gone / "scripts" / "host.py").write_text("")
    host.ensure_plugin_link(onboarded_sample, gone)
    shutil.rmtree(gone)
    assert _by_id(_run(onboarded_sample), "host.plugin_link").status == WARN


def test_root_export_manual_when_withheld(onboarded_for, monkeypatch):
    import project_files
    root = _codex_root(onboarded_for, monkeypatch)
    (root / ".codex" / "config.toml").write_text('[shell_environment_policy]\ninherit = "all"\n', encoding="utf-8")
    f = _by_id(_run(root), "host.root_export_manual")
    assert f.status == WARN and project_files.export_line() in f.observed
    assert "by hand" in f.remediation


def test_agents_md_size_warns_over_28_kib(onboarded_for, monkeypatch):
    root = _codex_root(onboarded_for, monkeypatch)
    assert not any(f.id == "host.agents_md_size" for f in _all(_run(root)))
    agents = root / "AGENTS.md"
    agents.write_text(agents.read_text(encoding="utf-8") + "x" * (28 * 1024) + "\n", encoding="utf-8")
    f = _by_id(_run(root), "host.agents_md_size")
    assert f.status == WARN and str(agents.stat().st_size) in f.observed


def test_inlined_rules_drift_reported_on_codex(onboarded_for, monkeypatch):
    root = _codex_root(onboarded_for, monkeypatch)
    _set_cfg(root, "page_budget: 8", "page_budget: 9")
    f = _by_id(_run(root), "project-files.drift:AGENTS.md")
    assert f.status == WARN and "Page budget" in f.observed


def test_codex_checks_codex_files(onboarded_for, monkeypatch):
    root = _codex_root(onboarded_for, monkeypatch)
    r = _run(root)
    assert _by_id(r, "project-files.instructions_section").status == PASS
    assert _by_id(r, "project-files.rules").status == PASS
    agent = next((root / ".codex" / "agents").glob("ploma-*.toml"))
    agent.write_text(agent.read_text(encoding="utf-8") + "# mine\n", encoding="utf-8")
    rel = agent.relative_to(root).as_posix()
    assert _by_id(_run(root), f"project-files.drift:{rel}").status == WARN
    (root / "AGENTS.md").write_text("# mine\n", encoding="utf-8")
    assert _by_id(_run(root), "project-files.instructions_section").status == WARN


def test_codex_superpowers_uses_host_paths(onboarded_for, monkeypatch, tmp_path):
    root = _codex_root(onboarded_for, monkeypatch)
    home = tmp_path / "home"
    assert _by_id(doctor.run(root, which=_which(), home=home), "dependencies.superpowers").status == WARN
    (home / ".codex" / "superpowers").mkdir(parents=True)
    assert _by_id(doctor.run(root, which=_which(), home=home), "dependencies.superpowers").status == PASS


def test_codex_ready_on_onboarded_sample(onboarded_for, monkeypatch, tmp_path, repo_root):
    root = _codex_root(onboarded_for, monkeypatch)
    home = tmp_path / "home"
    (home / ".agents" / "skills" / "superpowers").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    host.ensure_plugin_link(root, repo_root)
    r = doctor.run(root, which=_which())  # the toolchain stub every READY test uses; home comes from HOME
    assert r.verdict in ("READY", "READY_WITH_WARNINGS"), r.render()
    assert [f.id for f in _all(r) if f.status in (WARN, FAIL)] == [], r.render()


def test_remediation_is_localized(onboarded_for, monkeypatch):
    root = _codex_root(onboarded_for, monkeypatch)
    (root / "main.pdf").unlink()  # gives a remediation naming a skill
    txt = _run(root).render()
    assert "$ploma:compile" in txt and "/ploma:" not in txt


def test_plugin_link_to_another_plugin_version_warns(onboarded_sample, monkeypatch, tmp_path, repo_root):
    monkeypatch.setenv("PLOMA_HOST", "claude")
    assert not any(f.id == "host.plugin_link_version" for f in _all(_run(onboarded_sample)))
    old = tmp_path / "ploma-0.1.9"
    (old / "scripts").mkdir(parents=True)
    (old / "scripts" / "host.py").write_text("")
    host.ensure_plugin_link(onboarded_sample, old)
    r = _run(onboarded_sample)
    assert _by_id(r, "host.plugin_link").status == PASS
    f = _by_id(r, "host.plugin_link_version")
    assert f.status == WARN and str(old) in f.observed
    assert f.remediation == "Start a new session so the hook refreshes .ploma/plugin, or run /ploma:onboard."


def test_mismatch_skips_the_running_hosts_wiring(onboarded_sample, monkeypatch):
    """M4: on a mismatch, root export, plugin link and AGENTS.md size are not checked for the running host."""
    monkeypatch.setenv("PLOMA_HOST", "codex")
    (onboarded_sample / "AGENTS.md").write_text("x" * (29 * 1024), encoding="utf-8")
    ids = {f.id for f in _all(_run(onboarded_sample))}
    assert "host.host_mismatch" in ids
    assert not any(i.startswith(("host.root_export", "host.plugin_link", "host.agents_md_size")) for i in ids), ids


def test_not_onboarded_still_reports_the_plugin_link(sample_paper, monkeypatch):
    monkeypatch.setenv("PLOMA_HOST", "codex")
    r = _run(sample_paper)
    assert _by_id(r, "host.not_onboarded").status == INFO
    assert _by_id(r, "host.plugin_link").status == WARN


def test_render_reads_host_json_from_cwd(onboarded_for, monkeypatch):
    """M4: a plain shell in a Codex repo renders $ploma: from .ploma/host.json."""
    from _findings import Finding, render
    root = onboarded_for("codex")
    monkeypatch.chdir(root)
    assert host.read_host_json(root)["host"] == "codex"  # apply rewrote the Claude record on the switch
    assert render([Finding("a.b", WARN, "run /ploma:compile")]) == "- WARN a.b: run $ploma:compile"
