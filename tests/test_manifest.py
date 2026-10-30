"""Python manifest validator: runs in CI where the Claude CLI is absent."""
import json


def test_plugin_manifest_shape(repo_root):
    m = json.loads((repo_root / ".claude-plugin/plugin.json").read_text())
    assert m["name"] == "ploma"
    assert m["version"] == "0.2.0"
    assert m["license"] == "Apache-2.0"
    for key in ("skills", "agents", "hooks"):
        if key in m:
            vals = m[key] if isinstance(m[key], list) else [m[key]]
            assert all(v.startswith("./") for v in vals)


def test_marketplace_entry_matches_manifest(repo_root):
    mk = json.loads((repo_root / ".claude-plugin/marketplace.json").read_text())
    assert mk["name"] == "ploma"
    assert mk["plugins"][0]["name"] == "ploma"
    assert mk["plugins"][0]["source"] == "./"


def test_no_bin_dir_and_no_root_claude_md(repo_root):
    assert not (repo_root / "bin").exists()
    assert not (repo_root / "CLAUDE.md").exists()


def test_every_skill_dir_has_skill_md(repo_root):
    for d in (repo_root / "skills").iterdir():
        if d.is_dir() and not d.name.startswith("_"):
            assert (d / "SKILL.md").exists(), d
