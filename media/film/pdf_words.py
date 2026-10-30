#!/usr/bin/env python3
"""Word boxes for the film's PDF reveal.

Usage: python3 pdf_words.py <main.pdf> <out.json>

Runs `pdftotext -bbox-layout` on page 1 and keeps the words of the first
Introduction paragraph: every word after the heading "Introduction", up to
and including the first word that starts with "27.4". That is the paragraph
ploma rewrote. Each word is written as fractions of the page:
{"text", "x", "y", "w", "h"}.

It also renders page 1 with `pdftoppm -r 200` to assets/page-1.png, next to
this script. The film lays the word masks over that image.
"""
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
NS = "{http://www.w3.org/1999/xhtml}"


def page_words(pdf):
    xhtml = subprocess.run(
        ["pdftotext", "-bbox-layout", "-f", "1", "-l", "1", str(pdf), "-"],
        check=True, capture_output=True, text=True).stdout
    page = ET.fromstring(xhtml).find(f".//{NS}page")
    pw, ph = float(page.get("width")), float(page.get("height"))
    for word in page.iter(f"{NS}word"):
        x0, y0 = float(word.get("xMin")), float(word.get("yMin"))
        x1, y1 = float(word.get("xMax")), float(word.get("yMax"))
        yield {"text": word.text or "",
               "x": round(x0 / pw, 5), "y": round(y0 / ph, 5),
               "w": round((x1 - x0) / pw, 5), "h": round((y1 - y0) / ph, 5)}


def intro_paragraph(words):
    out, inside = [], False
    for w in words:
        if not inside:
            inside = w["text"] == "Introduction"
            continue
        out.append(w)
        if w["text"].startswith("27.4"):
            return out
    raise SystemExit("pdf_words.py: no Introduction paragraph ending in 27.4 on page 1")


def main():
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    pdf, out = Path(sys.argv[1]), Path(sys.argv[2])
    words = intro_paragraph(page_words(pdf))
    out.write_text(json.dumps(words, indent=1) + "\n")
    (HERE / "assets").mkdir(exist_ok=True)
    subprocess.run(["pdftoppm", "-r", "200", "-png", "-f", "1", "-l", "1",
                    str(pdf), str(HERE / "assets" / "page")], check=True)
    print(f"{len(words)} words -> {out}")


if __name__ == "__main__":
    main()
