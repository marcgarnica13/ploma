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
