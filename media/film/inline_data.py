#!/usr/bin/env python3
"""Inline script.json and pdf_words.json into compositions/main.html.

Usage: python3 inline_data.py

Rewrites the lines between "// BEGIN DATA" and "// END DATA" so the
composition carries its data and makes no fetch at render time. Run it after
editing either JSON file and before rendering. tests/test_film.py checks that
the inlined data matches the files.
"""
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAIN = HERE / "compositions" / "main.html"
BLOCK = re.compile(r"(// BEGIN DATA\n).*?(\n\s*// END DATA)", re.S)


def main():
    script = json.loads((HERE / "script.json").read_text())
    words = json.loads((HERE / "pdf_words.json").read_text())
    data = ("  var SCRIPT = " + json.dumps(script, separators=(",", ":")) + ";\n"
            "  var WORDS = " + json.dumps(words, separators=(",", ":")) + ";")
    html = MAIN.read_text()
    new, n = BLOCK.subn(lambda m: m.group(1) + data + m.group(2), html)
    if n != 1:
        raise SystemExit("inline_data.py: no single DATA block in compositions/main.html")
    MAIN.write_text(new)
    print(f"inlined {len(script['beats'])} beats and {len(words)} words")


if __name__ == "__main__":
    main()
