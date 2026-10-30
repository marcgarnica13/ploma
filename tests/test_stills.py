import re, struct
from conftest import REPO_ROOT

STILLS = ["grill", "spec", "write", "ship"]

def test_stills_exist_1400_wide_and_small():
    for n in STILLS:
        p = REPO_ROOT / "assets" / "stills" / f"{n}.png"
        b = p.read_bytes()
        assert b[:8] == b"\x89PNG\r\n\x1a\n"
        w, h = struct.unpack(">II", b[16:24])
        assert w == 1400 and 600 <= h <= 1000, (n, w, h)
        assert len(b) <= 300_000, (n, len(b))

def test_still_text_traces_to_transcripts():
    corpus = "\n".join(p.read_text() for p in (REPO_ROOT / "media" / "transcripts").glob("*.md"))
    for n in STILLS:
        html = (REPO_ROOT / "media" / "stills" / f"{n}.html").read_text()
        for m in re.finditer(r'<span class="ln"[^>]*>(.*?)</span>', html, re.S):
            line = re.sub(r"<[^>]+>", "", m.group(1)).strip()
            if line:
                assert line in corpus, (n, line)
