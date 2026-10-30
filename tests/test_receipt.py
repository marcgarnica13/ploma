"""Tests for the onboard apply receipt (scripts/receipt.py)."""
from __future__ import annotations

import json
import os

import pytest

import receipt


def _apply(root, rel, text, mode="enforced"):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return {"path": rel, "mode": mode, "sha256": receipt.sha256_file(p)}


def test_load_on_fresh_repo_is_none(sample_paper, cfg):
    assert receipt.load(sample_paper, cfg) is None


def test_write_then_compare_unchanged(sample_paper, cfg, repo_root):
    files = [_apply(sample_paper, ".claude/rules/a.md", "rule\n"),
             _apply(sample_paper, "CLAUDE.md", "hello\n", mode="merged")]
    out = receipt.write(sample_paper, cfg, files, "claude")
    assert out == sample_paper / "quality_reports" / "ploma-receipt.json"
    data = json.loads(out.read_text())
    manifest = json.loads((repo_root / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert data["ploma_version"] == manifest["version"] and data["at"].endswith("Z")
    assert [f["path"] for f in data["files"]] == [".claude/rules/a.md", "CLAUDE.md"]
    assert receipt.load(sample_paper, cfg) == data
    assert receipt.compare(sample_paper, cfg) == [
        {"path": ".claude/rules/a.md", "mode": "enforced", "state": "unchanged"},
        {"path": "CLAUDE.md", "mode": "merged", "state": "unchanged"}]


def test_edit_is_hand_edited_and_delete_is_missing(sample_paper, cfg):
    files = [_apply(sample_paper, "a.md", "one\n"), _apply(sample_paper, "b.md", "two\n", "created-once")]
    receipt.write(sample_paper, cfg, files, "claude")
    (sample_paper / "a.md").write_text("one, edited\n", encoding="utf-8")
    (sample_paper / "b.md").unlink()
    states = {r["path"]: r["state"] for r in receipt.compare(sample_paper, cfg)}
    assert states == {"a.md": "hand_edited", "b.md": "missing"}


def test_compare_without_receipt_is_empty(sample_paper, cfg):
    assert receipt.compare(sample_paper, cfg) == []


def test_unknown_mode_rejected(sample_paper, cfg):
    f = _apply(sample_paper, "a.md", "x\n", mode="enforced")
    f["mode"] = "sometimes"
    with pytest.raises(ValueError, match="mode"):
        receipt.write(sample_paper, cfg, [f], "claude")


def test_paths_normalised_and_unsafe_paths_rejected(sample_paper, cfg):
    f = _apply(sample_paper, "sub/a.md", "x\n")
    receipt.write(sample_paper, cfg, [dict(f, path="./sub//a.md")], "claude")
    assert receipt.load(sample_paper, cfg)["files"][0]["path"] == "sub/a.md"
    for bad in (str(sample_paper / "sub" / "a.md"), "../x", "sub/../../x", "/etc/passwd"):
        with pytest.raises(ValueError, match="receipt path"):
            receipt.write(sample_paper, cfg, [dict(f, path=bad)], "claude")


def test_hand_edited_receipt_with_parent_path_rejected(sample_paper, cfg):
    receipt.write(sample_paper, cfg, [_apply(sample_paper, "a.md", "x\n")], "claude")
    p = sample_paper / "quality_reports" / "ploma-receipt.json"
    data = json.loads(p.read_text())
    data["files"][0]["path"] = "../x"
    p.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match=r"ploma-receipt\.json.*\.\./x"):
        receipt.load(sample_paper, cfg)
    with pytest.raises(ValueError, match="ploma-receipt.json"):
        receipt.compare(sample_paper, cfg)
    assert receipt.main(["--root", str(sample_paper), "compare"]) == 2


@pytest.mark.skipif(not hasattr(os, "geteuid") or os.geteuid() == 0, reason="root can read mode 000 files")
def test_unreadable_target_exits_2(sample_paper, cfg, capsys):
    receipt.write(sample_paper, cfg, [_apply(sample_paper, "a.md", "x\n")], "claude")
    target = sample_paper / "a.md"
    target.chmod(0)
    try:
        assert receipt.main(["--root", str(sample_paper), "compare"]) == 2
        err = capsys.readouterr().err.strip()
        assert "a.md" in err and len(err.splitlines()) == 1
    finally:
        target.chmod(0o644)


def test_malformed_receipt_names_file(sample_paper, cfg):
    p = sample_paper / "quality_reports" / "ploma-receipt.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError, match="ploma-receipt.json"):
        receipt.load(sample_paper, cfg)
    p.write_text(json.dumps({"ploma_version": "0.1.0", "at": "x", "files": [{"path": "a"}]}), encoding="utf-8")
    with pytest.raises(ValueError, match="ploma-receipt.json"):
        receipt.load(sample_paper, cfg)


def test_sha256_file(tmp_path):
    p = tmp_path / "x"
    p.write_bytes(b"abc")
    assert receipt.sha256_file(p) == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def test_cli_compare(sample_paper, cfg, capsys):
    receipt.write(sample_paper, cfg, [_apply(sample_paper, "a.md", "x\n")], "claude")
    assert receipt.main(["--root", str(sample_paper), "--json", "compare"]) == 0
    assert json.loads(capsys.readouterr().out)[0]["state"] == "unchanged"
    (sample_paper / "a.md").write_text("y\n", encoding="utf-8")
    assert receipt.main(["--root", str(sample_paper), "compare"]) == 1
    assert "hand_edited" in capsys.readouterr().out


def test_write_stores_host_and_load_defaults_to_claude(sample_paper, cfg):
    out = receipt.write(sample_paper, cfg, [_apply(sample_paper, "a.md", "x\n")], "codex")
    assert json.loads(out.read_text())["host"] == "codex" and receipt.load(sample_paper, cfg)["host"] == "codex"
    data = json.loads(out.read_text())
    del data["host"]
    out.write_text(json.dumps(data), encoding="utf-8")
    assert receipt.load(sample_paper, cfg)["host"] == "claude"
    data["host"] = 3
    out.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="host"):
        receipt.load(sample_paper, cfg)
