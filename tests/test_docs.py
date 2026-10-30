import re
from conftest import REPO_ROOT
from _banned import EM_DASH_RE

DOCS = {"install.md": ["Claude Code", "Codex", "Updates", "API keys"],
        "hosts.md": ["Switching hosts", "Co-authors on Codex"],
        "commit-gate.md": ["Required and recommended checks", "Overrides", "Checking the gate"],
        "testing.md": ["Running the tests", "Field tests", "Evals"]}

def _links(text):
    return [m.group(1) for m in re.finditer(r"\]\(([^)#]+)(?:#[^)]*)?\)", text) if not m.group(1).startswith(("http", "mailto"))]

def test_docs_exist_with_expected_sections():
    for name, h2s in DOCS.items():
        text = (REPO_ROOT / "docs" / name).read_text()
        assert text.count("\n# ") + text.startswith("# ") == 1
        for h in h2s:
            assert f"\n## {h}\n" in text, (name, h)

def test_docs_have_no_dashes_and_links_resolve():
    for name in DOCS:
        path = REPO_ROOT / "docs" / name
        text = path.read_text()
        assert not EM_DASH_RE.search(text), name
        for link in _links(text):
            assert (path.parent / link).resolve().exists(), (name, link)
