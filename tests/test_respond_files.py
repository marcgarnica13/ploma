"""respond_files.py: archive a response round and delete respond's mktemp files (R158)."""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

import respond_files


def _response(root: Path) -> Path:
    out = root / "quality_reports"
    out.mkdir(exist_ok=True)
    (out / "response_to_referees.md").write_text("**Response round:** 1\n", encoding="utf-8")
    (out / "response_to_referees_matrix.csv").write_text("id,reviewer\n", encoding="utf-8")
    return out


def test_archive_round_renames_both_files(sample_paper, cfg):
    out = _response(sample_paper)
    assert respond_files.main(["--root", str(sample_paper), "archive-round", "1", "--json"]) == 0
    assert (out / "response_to_referees_r1.md").read_text(encoding="utf-8").startswith("**Response round:** 1")
    assert (out / "response_to_referees_matrix_r1.csv").is_file()
    assert not (out / "response_to_referees.md").exists() and not (out / "response_to_referees_matrix.csv").exists()


def test_archive_round_refuses_to_overwrite(sample_paper, cfg, capsys):
    out = _response(sample_paper)
    (out / "response_to_referees_r1.md").write_text("old\n", encoding="utf-8")
    assert respond_files.main(["--root", str(sample_paper), "archive-round", "1", "--json"]) == 1
    assert "already exists" in json.loads(capsys.readouterr().out)["error"]
    assert (out / "response_to_referees.md").is_file()
    assert (out / "response_to_referees_r1.md").read_text(encoding="utf-8") == "old\n"


def test_archive_round_without_a_response(sample_paper, cfg):
    assert respond_files.main(["--root", str(sample_paper), "archive-round", "2"]) == 1


def test_clean_tmp_deletes_only_mktemp_files(tmp_path, monkeypatch):
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    made = subprocess.run(["mktemp", "--suffix=.txt"], capture_output=True, text=True,
                          env={**os.environ, "TMPDIR": str(tmp_path)}).stdout.strip()
    other = tmp_path / "notes.txt"
    other.write_text("keep\n")
    nested = tmp_path / "sub"
    nested.mkdir()
    deep = nested / "tmp.abc"
    deep.write_text("keep\n")
    link = tmp_path / "tmp.link"
    link.symlink_to(other)
    assert respond_files.main(["clean-tmp", made, str(other), str(deep), str(link)]) == 1
    assert not Path(made).exists()
    assert other.is_file() and deep.is_file() and link.is_symlink()


def test_clean_tmp_all_ok_exits_0(tmp_path, monkeypatch):
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    f = tmp_path / "tmp.XYZ123.txt"
    f.write_text("x")
    assert respond_files.main(["clean-tmp", str(f)]) == 0 and not f.exists()


def test_usage_errors():
    assert respond_files.main([]) == 2
    assert respond_files.main(["archive-round"]) == 2
