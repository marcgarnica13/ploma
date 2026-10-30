"""Logo assets: SVG hygiene and the 512 px plugin icon."""
import struct
import xml.etree.ElementTree as ET

from conftest import REPO_ROOT
from _banned import EM_DASH_RE

LOGO = REPO_ROOT / "assets" / "logo"
SVGS = ["ploma-mark.svg", "ploma-mark-dark.svg", "ploma-lockup.svg", "ploma-lockup-dark.svg"]


def _png_size(path):
    b = path.read_bytes()
    assert b[:8] == b"\x89PNG\r\n\x1a\n"
    return struct.unpack(">II", b[16:24])


def test_svgs_parse_have_viewbox_and_explicit_colours():
    for name in SVGS:
        text = (LOGO / name).read_text()
        root = ET.fromstring(text)
        assert root.get("viewBox")
        assert "currentColor" not in text
        assert ("#e8e6e0" in text) == name.endswith("-dark.svg")
        assert ("#1d1b17" in text) != name.endswith("-dark.svg")


def test_lockups_are_outlined_not_text():
    for name in ("ploma-lockup.svg", "ploma-lockup-dark.svg"):
        assert "<text" not in (LOGO / name).read_text()


def test_svgs_have_no_dashes():
    for name in SVGS:
        assert not EM_DASH_RE.search((LOGO / name).read_text()), name


def test_icon_is_the_512_nib():
    assert _png_size(LOGO / "ploma-mark-512.png") == (512, 512)
    assert _png_size(REPO_ROOT / ".claude-plugin" / "icon.png") == (512, 512)
    assert (LOGO / "ploma-mark-512.png").read_bytes() == (REPO_ROOT / ".claude-plugin" / "icon.png").read_bytes()
