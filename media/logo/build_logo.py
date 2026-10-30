"""Build the ploma logo: the nib mark, the Fraunces wordmark lockup and the plugin icon.

Run with no arguments from anywhere:

    python3 media/logo/build_logo.py

Writes assets/logo/*.svg, assets/logo/ploma-mark-512.png and .claude-plugin/icon.png.
The Fraunces font is downloaded once into media/logo/.cache/ and never committed.
"""
from __future__ import annotations

import shutil
import subprocess
import urllib.request
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
OUT = REPO_ROOT / "assets" / "logo"
ICON = REPO_ROOT / ".claude-plugin" / "icon.png"
CACHE = HERE / ".cache"
FONT = CACHE / "Fraunces[SOFT,WONK,opsz,wght].ttf"
FONT_URL = ("https://raw.githubusercontent.com/google/fonts/main/ofl/fraunces/"
            "Fraunces%5BSOFT%2CWONK%2Copsz%2Cwght%5D.ttf")

LIGHT = "#1d1b17"
DARK = "#e8e6e0"

STROKE = 6
OUTLINE = "M50 8 C62 26 74 44 74 60 C74 76 63 88 50 92 C37 88 26 76 26 60 C26 44 38 26 50 8 Z"
SLIT = "M50 52 V92"

WORD = "ploma"
AXES = {"opsz": 72, "wght": 500}
TRACKING = -0.02  # em

# Lockup layout, in lockup user units.
HEIGHT = 80
MARGIN = 4
MARK_SIZE = 60                      # the mark's 100 unit box drawn 60 units tall
MARK_SCALE = MARK_SIZE / 100
MARK_Y = (HEIGHT - MARK_SIZE) / 2   # box top
# Shift left so the outline's ink (x 26 minus half the stroke) starts at the margin.
MARK_X = MARGIN - (26 - STROKE / 2) * MARK_SCALE
BASELINE = MARK_Y + 92 * MARK_SCALE  # bottom of the slit
GAP = 10                              # from the mark's right ink edge to the wordmark
WORD_X = MARK_X + (74 + STROKE / 2) * MARK_SCALE + GAP
FONT_SIZE = 40                        # em size of the wordmark, in user units


def _mark_body(colour: str) -> str:
    return (
        f'<path d="{OUTLINE}" fill="none" stroke="{colour}" stroke-width="{STROKE}" '
        f'stroke-linejoin="round" stroke-linecap="round"/>'
        f'<path d="{SLIT}" fill="none" stroke="{colour}" stroke-width="{STROKE}" '
        f'stroke-linecap="round"/>'
        f'<circle cx="50" cy="48" r="5" fill="{colour}"/>'
    )


def mark_svg(colour: str) -> str:
    """The nib mark alone, in a 100 by 100 box."""
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">'
        '<title>ploma</title>'
        f'{_mark_body(colour)}'
        '</svg>\n'
    )


def _fetch_font() -> Path:
    if not FONT.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        tmp = FONT.with_suffix(".part")
        with urllib.request.urlopen(FONT_URL) as resp, open(tmp, "wb") as fh:
            shutil.copyfileobj(resp, fh)
        tmp.replace(FONT)
    return FONT


def _word_layout(font: Path) -> tuple[list[str], float]:
    """Glyph path data in font units, each already offset along x, plus the total advance."""
    tt = instantiateVariableFont(TTFont(font), AXES)
    cmap = tt.getBestCmap()
    glyphs = tt.getGlyphSet()
    upm = tt["head"].unitsPerEm
    track = TRACKING * upm
    x = 0.0
    paths = []
    for i, ch in enumerate(WORD):
        name = cmap[ord(ch)]
        pen = SVGPathPen(glyphs)
        glyphs[name].draw(pen)
        paths.append(f'<path transform="translate({x:g} 0)" d="{pen.getCommands()}"/>')
        x += tt["hmtx"][name][0]
        if i < len(WORD) - 1:
            x += track
    return paths, x / upm


def wordmark_paths(font: Path) -> str:
    """The word "ploma" as outlined paths in a <g>, placed on the lockup baseline."""
    tt = TTFont(font)
    upm = tt["head"].unitsPerEm
    paths, _ = _word_layout(font)
    s = FONT_SIZE / upm
    return (
        f'<g transform="translate({WORD_X:g} {BASELINE:g}) scale({s:g} {-s:g})">'
        + "".join(paths)
        + "</g>"
    )


def _lockup_width(font: Path) -> float:
    _, advance_em = _word_layout(font)
    return WORD_X + advance_em * FONT_SIZE + MARGIN


def lockup_svg(colour: str, word_paths: str, width: float | None = None) -> str:
    """The mark at the left and the wordmark to its right, on one baseline."""
    w = round(width if width is not None else 320, 2)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:g} {HEIGHT}" '
        f'width="{w:g}" height="{HEIGHT}">'
        '<title>ploma</title>'
        f'<g transform="translate({MARK_X:g} {MARK_Y:g}) scale({MARK_SCALE:g})">'
        f'{_mark_body(colour)}</g>'
        f'<g fill="{colour}">{word_paths}</g>'
        '</svg>\n'
    )


def main() -> None:
    font = _fetch_font()
    OUT.mkdir(parents=True, exist_ok=True)
    word = wordmark_paths(font)
    width = _lockup_width(font)
    (OUT / "ploma-mark.svg").write_text(mark_svg(LIGHT))
    (OUT / "ploma-mark-dark.svg").write_text(mark_svg(DARK))
    (OUT / "ploma-lockup.svg").write_text(lockup_svg(LIGHT, word, width))
    (OUT / "ploma-lockup-dark.svg").write_text(lockup_svg(DARK, word, width))
    png = OUT / "ploma-mark-512.png"
    subprocess.run(["rsvg-convert", "-w", "512", "-h", "512", str(OUT / "ploma-mark.svg"),
                    "-o", str(png)], check=True)
    shutil.copyfile(png, ICON)


if __name__ == "__main__":
    main()
