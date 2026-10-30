# tests/test_render_transcript.py
import importlib.util, json
from conftest import REPO_ROOT

def _mod():
    spec = importlib.util.spec_from_file_location("rt", REPO_ROOT / "media" / "transcripts" / "render_transcript.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def test_render_user_assistant_and_tool_lines():
    events = [
        {"type": "user", "message": {"role": "user", "content": "/ploma:write intro"}},
        {"type": "assistant", "message": {"role": "assistant", "content": [
            {"type": "text", "text": "Draft: sections/intro_suggestion.tex"},
            {"type": "tool_use", "name": "Bash", "input": {"command": "python3 scripts/style_check.py --root . x"}}]}},
    ]
    out = _mod().render(events)
    assert out.splitlines()[0] == "> /ploma:write intro"
    assert "Draft: sections/intro_suggestion.tex" in out
    assert "[tool] Bash python3 scripts/style_check.py --root . x" in out
