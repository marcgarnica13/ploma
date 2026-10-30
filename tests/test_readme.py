import json, re
from conftest import REPO_ROOT
from _banned import EM_DASH_RE

README = (REPO_ROOT / "README.md").read_text()

def _refs(text):
    md = re.findall(r"\]\(([^)#\s]+)", text)
    html = re.findall(r'(?:src|srcset|href)="([^"#]+)"', text)
    return [r for r in md + html if not r.startswith(("http", "mailto"))]

def test_readme_and_docs_have_no_dashes():
    for p in [REPO_ROOT / "README.md", *(REPO_ROOT / "docs").glob("*.md")]:
        assert not EM_DASH_RE.search(p.read_text()), p

def test_every_relative_reference_resolves():
    for r in _refs(README):
        assert (REPO_ROOT / r).exists(), r

def test_asset_references_are_relative():
    assert "raw.githubusercontent.com" not in README
    assert "assets/film/ploma-hero.gif" in README

def test_logo_picture_has_both_schemes():
    assert 'media="(prefers-color-scheme: dark)"' in README and "ploma-lockup-dark.svg" in README
    assert "ploma-lockup.svg" in README

def test_sections_in_spec_order():
    heads = [h for h in re.findall(r"^## (.+)$", README, re.M)]
    assert heads == ["Why ploma exists", "How a paper gets written", "What stops slop", "Install in two minutes", "The full lifecycle", "Trust and testing", "Credits and licence"]

def test_demo_paper_is_declared_fictional_and_version_matches():
    assert "examples/demo-paper" in README and "fictional" in README
    version = json.loads((REPO_ROOT / ".claude-plugin" / "plugin.json").read_text())["version"]
    assert version in README
    assert "## Unreleased" in (REPO_ROOT / "CHANGELOG.md").read_text()
