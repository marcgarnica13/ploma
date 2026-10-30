import json
from conftest import REPO_ROOT

FILM = REPO_ROOT / "media" / "film"
OUT = REPO_ROOT / "assets" / "film"

def test_film_script_lines_trace_to_transcripts():
    corpus = "\n".join(p.read_text() for p in (REPO_ROOT / "media" / "transcripts").glob("*.md"))
    script = json.loads((FILM / "script.json").read_text())
    names = [b["name"] for b in script["beats"]]
    assert names == ["open", "grill", "write", "ship", "tagline"]
    for beat in script["beats"]:
        for line in beat["lines"]:
            assert line["text"] in corpus, (beat["name"], line["text"])

def test_pdf_words_cover_the_grounded_number():
    words = json.loads((FILM / "pdf_words.json").read_text())
    assert any(w["text"].startswith("27.4") for w in words)
    assert all(0 <= w["x"] <= 1 and 0 <= w["y"] <= 1 for w in words)

def test_outputs_exist_and_fit_the_budget():
    gif = (OUT / "ploma-hero.gif").read_bytes()
    assert gif[:6] == b"GIF89a" and len(gif) <= 6_000_000
    assert (OUT / "ploma-hero.png").read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    mp4 = OUT / "ploma-hero.mp4"
    assert not mp4.exists() or mp4.stat().st_size <= 4_000_000

def test_composition_inlines_the_current_data():
    html = (FILM / "compositions" / "main.html").read_text()
    script = json.loads((FILM / "script.json").read_text())
    words = json.loads((FILM / "pdf_words.json").read_text())
    assert "fetch(" not in html
    assert "var SCRIPT = " + json.dumps(script, separators=(",", ":")) + ";" in html
    assert "var WORDS = " + json.dumps(words, separators=(",", ":")) + ";" in html
