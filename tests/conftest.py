"""Shared pytest fixtures for ploma."""
import shutil
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

for _sub in ("scripts", "hooks"):
    _p = str(REPO_ROOT / _sub)
    if _p not in sys.path:
        sys.path.insert(0, _p)


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture
def sample_paper(tmp_path) -> Path:
    src = REPO_ROOT / "examples" / "sample-paper"
    if not src.is_dir():
        pytest.skip("examples/sample-paper not created yet")
    dst = tmp_path / "sample-paper"
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("build"))
    return dst


@pytest.fixture
def cfg(sample_paper) -> dict:
    import ploma_config
    return ploma_config.load(sample_paper)


@pytest.fixture
def onboarded_sample(sample_paper) -> Path:
    """sample_paper as onboard leaves it (Ruling R1): superpowers enabled, .gitignore, a fresh PDF,
    and the project files applied (rules, CLAUDE.md section, outputs README, learnings, state, receipt)."""
    import json
    import os

    import host
    import ploma_config
    import project_files

    claude = sample_paper / ".claude"
    claude.mkdir(exist_ok=True)
    (claude / "settings.json").write_text(
        json.dumps({"enabledPlugins": {"superpowers@claude-plugins-official": True}}, indent=2) + "\n",
        encoding="utf-8")
    (sample_paper / ".gitignore").write_text(".ploma/\nquality_reports/session_logs/\n", encoding="utf-8")
    pdf = sample_paper / "main.pdf"
    shutil.copyfile(sample_paper / "figures" / "fig1.pdf", pdf)
    newest = max(p.stat().st_mtime for p in sample_paper.rglob("*") if p.suffix in (".tex", ".bib"))
    os.utime(pdf, (newest + 60, newest + 60))
    cfg = ploma_config.load(sample_paper)
    claude_host = host.HOSTS["claude"]
    project_files.apply(sample_paper, cfg, project_files.plan(sample_paper, cfg, claude_host), claude_host)
    return sample_paper


@pytest.fixture
def onboarded_for(onboarded_sample):
    """A function: onboarded_for(name) applies host name's plan on top of the Claude-onboarded sample,
    so both file sets exist and the receipt names the new host; returns the repo root."""
    import host
    import ploma_config
    import project_files

    def make(name: str) -> Path:
        h = host.HOSTS[name]
        cfg = ploma_config.load(onboarded_sample)
        project_files.apply(onboarded_sample, cfg, project_files.plan(onboarded_sample, cfg, h), h)
        return onboarded_sample

    return make
